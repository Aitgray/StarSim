import sys
from pathlib import Path
from collections import defaultdict, deque
import random
import json
from typing import Dict, List, Set, Tuple, Optional

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, render_template, jsonify, request

from src.starsim.core.state import UniverseState
from src.starsim.core.ids import CommodityId, WorldId # Import WorldId for updating universe.worlds
from src.starsim.generation.system_gen import generate_universe
from src.starsim.generation.load import load_planet_types, load_system_templates
from src.starsim.world.load import load_universe # Corrected import for load_universe
from src.starsim.generation.bootstrap import apply_planet_potentials_to_world
from src.starsim.generation.lane_gen import generate_non_intersecting_lanes # Import new lane generation
from src.starsim.factions.model import Faction, WorldFactionState # Imported for WorldFactionState control


app = Flask(__name__)

# Load generation data once on startup
# Assuming data files are relative to the project root
DATA_PATH = Path(__file__).parent.parent / "data"
PLANET_TYPES = load_planet_types(DATA_PATH / "generation" / "planet_types.yaml")
SYSTEM_TEMPLATES = load_system_templates(DATA_PATH / "generation" / "system_templates.yaml")

# Global variables to store the universe state and cached data
universe = None
cached_nodes = []
cached_edges = []
cached_factions = []

# --- Helper for shortest path in hops (BFS) ---
def _get_shortest_path_hops(lane_graph: Dict[WorldId, List[WorldId]], start_node: WorldId, target_nodes: Set[WorldId], min_hops: int) -> Optional[int]:
    """
    Calculates the shortest path in hops from start_node to any target_node within min_hops.
    Returns the number of hops, or None if no path found within min_hops.
    """
    if start_node in target_nodes:
        return 0 # The node itself is a target

    queue = deque([(start_node, 0)]) # (node, hops)
    visited = {start_node}

    while queue:
        current_node, hops = queue.popleft()

        if hops >= min_hops: # If we reached max_hops, no need to go further down this path
            continue

        for neighbor in lane_graph.get(current_node, []):
            if neighbor in target_nodes:
                return hops + 1 # Found a target node, return hops to it
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, hops + 1))
    return None # No path found to any target within min_hops


def _initialize_universe_and_cache():
    global universe, cached_nodes, cached_edges, cached_factions
    
    test_seed = 100 # Use a fixed seed for consistent generation
    rng = random.Random(test_seed)
    
    n_systems = 40 # Changed to 40 for testing purposes
    # First, load the base universe data from YAML (this includes factions, if any)
    # This also sets a seed, which generate_universe will reuse
    base_universe_state = load_universe(DATA_PATH / "universe.yaml")
    
    # Then, generate additional systems/lanes on top of this base state
    # This is where generate_universe populates worlds and lanes if initial_state doesn't have enough
    universe = generate_universe(rng, n_systems=n_systems, system_templates_data=SYSTEM_TEMPLATES, planet_types_data=PLANET_TYPES, initial_state=base_universe_state)
    print(f"DEBUG: Universe generated. universe.factions: {universe.factions}")

    for world_id, world in universe.worlds.items():
        apply_planet_potentials_to_world(world, universe)

    # Build lane_graph for BFS (used in capital assignment)
    lane_graph = defaultdict(list)
    for lane in universe.lanes.values(): # universe.lanes is populated by generate_universe
        lane_graph[lane.a].append(lane.b)
        lane_graph[lane.b].append(lane.a)

    # --- Capital Assignment Logic ---
    min_distance_hops = 3
    
    # Filter for worlds with at least one habitable planet
    all_habitable_worlds_ids = [
        world_id for world_id, world in universe.worlds.items()
        if any(p.type in ["continental", "ocean"] for p in world.planets) # Assuming these are habitable types
    ]
    random.shuffle(all_habitable_worlds_ids) # Randomize selection order for fairness

    assigned_capital_worlds_ids = set() # Keep track of worlds already assigned as capitals

    for faction_id, faction in universe.factions.items():
        # If capital_world_id is already defined in YAML, use that
        if faction.capital_world_id is not None:
            assigned_capital_worlds_ids.add(faction.capital_world_id)
            print(f"DEBUG: Faction {faction_id} capital loaded from YAML: {faction.capital_world_id}")
            continue 

        # Identify systems controlled by other factions (including already assigned capitals)
        other_faction_controlled_systems = set(assigned_capital_worlds_ids) # Start with already assigned capitals
        
        for other_fac_id, other_fac in universe.factions.items():
            if other_fac_id == faction_id:
                continue
            if other_fac.capital_world_id:
                other_faction_controlled_systems.add(other_fac.capital_world_id)
            
            # Also consider any world a *different* faction might already control
            # This requires WorldFactionState.control to be resolved for these worlds
            for world_id, world in universe.worlds.items():
                if world.factions: # Check if World has a WorldFactionState object
                    # world.factions is a WorldFactionState instance
                    wfs_instance = world.factions 
                    if wfs_instance.control == other_fac_id: # If another faction controls this world
                        other_faction_controlled_systems.add(world_id)

        # Filter suitable capital candidates for the current faction
        suitable_capital_candidates = []
        for candidate_world_id in all_habitable_worlds_ids:
            if candidate_world_id in assigned_capital_worlds_ids:
                continue # Already taken by another faction or this faction itself

            # If there are no other controlled systems, any habitable world is suitable
            if not other_faction_controlled_systems:
                suitable_capital_candidates.append(candidate_world_id)
                continue

            # Check distance to all other_faction_controlled_systems
            is_far_enough = True
            for other_controlled_system_id in other_faction_controlled_systems:
                hops_distance = _get_shortest_path_hops(lane_graph, candidate_world_id, {other_controlled_system_id}, min_distance_hops)
                # If a path exists and is shorter than min_distance_hops, then it's too close
                if hops_distance is not None and hops_distance < min_distance_hops:
                    is_far_enough = False
                    break
            
            if is_far_enough:
                suitable_capital_candidates.append(candidate_world_id)
        
        if suitable_capital_candidates:
            chosen_capital_id = suitable_capital_candidates[0] # Pick the first suitable from shuffled list
            universe.factions[faction_id].capital_world_id = chosen_capital_id
            assigned_capital_worlds_ids.add(chosen_capital_id)
            print(f"DEBUG: Assigned capital {chosen_capital_id} to faction {faction_id}")
            
            # Set this faction to control the capital world
            if chosen_capital_id in universe.worlds:
                world = universe.worlds[chosen_capital_id]
                # Ensure world.factions exists and is a dict before assigning
                if not world.factions:
                    world.factions = WorldFactionState() # Initialize if empty
                # Create or update WorldFactionState for the controlling faction
                if faction_id not in world.factions.influence: # Check if faction already has influence entry
                    world.factions.influence[faction_id] = 0.0 # Initialize to 0 before setting to 1.0
                world.factions.influence[faction_id] = 1.0 # Max influence
                world.factions.resolve_control() # Resolve control
        else:
            print(f"WARNING: Could not find suitable capital for faction {faction_id}. No habitable worlds far enough from others.")

    # --- End Capital Assignment Logic ---

    cached_factions = []
    for faction_id, faction in universe.factions.items():
        cached_factions.append({
            "id": str(faction.id),
            "name": faction.name,
            "color": faction.color,
            "capital_world_id": str(faction.capital_world_id) if faction.capital_world_id else None,
            "desired_resources": {str(cid): val for cid, val in faction.desired_resources.items()},
        })
    print(f"DEBUG: cached_factions populated: {cached_factions}")

    cached_nodes = []
    for world_id, world in universe.worlds.items():
        world_resources = defaultdict(float)
        detailed_planets = []

        for planet in world.planets:
            planet_resource_potentials = {str(cid): round(val, 2) for cid, val in planet.resource_potentials.items()}
            detailed_planets.append({
                "type": planet.type,
                "habitability": round(planet.habitability, 2),
                "resource_potentials": planet_resource_potentials
            })
            for commodity_id, potential_value in planet.resource_potentials.items():
                world_resources[str(commodity_id)] += round(potential_value, 2)

        world_factions_data = {}
        if world.factions: # Check if World has a WorldFactionState object
            wfs = world.factions 

            controlled_by_faction_id = None
            if wfs.control:
                controlled_by_faction_id = wfs.control
                world_factions_data[str(controlled_by_faction_id)] = {
                    "influence": wfs.influence.get(controlled_by_faction_id, 0.0),
                    "presence": True,
                    "controlled_by": True
                }
            
            # Then, add all other factions that have influence (if not the controller)
            for fac_id, influence_val in wfs.influence.items():
                if fac_id != controlled_by_faction_id: # Only add if not already handled as controller
                     world_factions_data[str(fac_id)] = {
                        "influence": influence_val,
                        "presence": True,
                        "controlled_by": False
                    }


        cached_nodes.append({
            "id": str(world.id),
            "name": world.name,
            "stability": round(world.stability, 2),
            "prosperity": round(world.prosperity, 2),
            "num_planets": len(world.planets),
            "aggregated_resources": dict(world_resources),
            "detailed_planets": detailed_planets,
            "x": world.x,
            "y": world.y,
            "factions": world_factions_data,
        })
    
    cached_edges = generate_non_intersecting_lanes(universe.worlds)

@app.before_request
def before_first_request():
    if universe is None:
        _initialize_universe_and_cache()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/universe_data')
def get_universe_data():
    return jsonify({"nodes": cached_nodes, "edges": cached_edges, "factions": cached_factions})

@app.route('/update_node_positions', methods=['POST'])
def update_node_positions():
    global universe, cached_nodes
    data = request.get_json()
    node_positions = data.get('node_positions')

    if not node_positions:
        return jsonify({"error": "Missing node_positions"}), 400

    if universe is None:
        return jsonify({"error": "Universe not initialized"}), 500

    # Update the global universe object's world coordinates
    for world_id_str, pos in node_positions.items():
        world_id = WorldId(world_id_str)
        if world_id in universe.worlds:
            universe.worlds[world_id].x = pos['x']
            universe.worlds[world_id].y = pos['y']
    
    # Update the cached_nodes as well for consistency
    for node_data in cached_nodes:
        if node_data["id"] in node_positions:
            node_data["x"] = node_positions[node_data["id"]]['x']
            node_data["y"] = node_positions[node_data["id"]]['y']

    return jsonify({"message": "Node positions updated successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True)