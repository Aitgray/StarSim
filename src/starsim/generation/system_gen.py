from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Any, Optional, Tuple
import random
import math

from ..core.ids import WorldId, CommodityId, LaneId
from ..core.state import UniverseState
from ..world.model import World, Lane
from .model import Planet
from .load import load_planet_types, load_system_templates, load_planet_names, load_system_names, _process_weights_for_random_selection
from .bootstrap import apply_planet_potentials_to_world

if TYPE_CHECKING:
    from ..core.state import UniverseState

# Added constants for world coordinate generation
WORLD_COORD_RANGE_X = (0, 800) # Roughly match visualizer SVG width
WORLD_COORD_RANGE_Y = (0, 600) # Roughly match visualizer SVG height

# Added constants for biased coordinate generation
WORLD_COORD_CENTER_X = (WORLD_COORD_RANGE_X[0] + WORLD_COORD_RANGE_X[1]) / 2
WORLD_COORD_CENTER_Y = (WORLD_COORD_RANGE_Y[0] + WORLD_COORD_RANGE_Y[1]) / 2
WORLD_COORD_STD_DEV = 150 # Standard deviation to control spread, adjust as needed


def _sample_from_range_or_bins(rng: random.Random, data: Dict[str, Any]) -> float:
    """Samples a value from a range or a set of weighted bins."""
    if "range" in data:
        min_val, max_val = data["range"]
        return rng.uniform(min_val, max_val)
    elif "bins" in data:
        choices, weights = _process_weights_for_random_selection(data["bins"])
        selected_bin = rng.choices(choices, weights=weights, k=1)[0]
        return selected_bin["value"]
    else:
        raise ValueError("Resource potential must define 'range' or 'bins'.")


def _get_connected_components(worlds: Dict[WorldId, World], lanes: Dict[LaneId, Lane]) -> List[Set[WorldId]]:
    """
    Finds all connected components in the graph of worlds and lanes using BFS.
    """
    adj_list = {world_id: [] for world_id in worlds.keys()}
    for lane in lanes.values():
        adj_list[lane.a].append(lane.b)
        adj_list[lane.b].append(lane.a)

    visited = set()
    components = []

    for world_id in worlds.keys():
        if world_id not in visited:
            current_component = set()
            queue = [world_id]
            visited.add(world_id)
            
            while queue:
                u = queue.pop(0)
                current_component.add(u)
                for v in adj_list[u]:
                    if v not in visited:
                        visited.add(v)
                        queue.append(v)
            components.append(current_component)
    return components

def _get_closest_worlds_between_components(
    component1: Set[WorldId], 
    component2: Set[WorldId], 
    worlds: Dict[WorldId, World]
) -> Tuple[WorldId, WorldId, float]:
    """
    Finds the closest pair of worlds between two disconnected components.
    Returns (world_id_a, world_id_b, distance).
    """
    min_distance = float('inf')
    closest_pair = (None, None) # type: ignore

    for world_id_a in component1:
        for world_id_b in component2:
            world_a = worlds[world_id_a]
            world_b = worlds[world_id_b]
            distance = math.sqrt((world_a.x - world_b.x)**2 + (world_a.y - world_b.y)**2)
            if distance < min_distance:
                min_distance = distance
                closest_pair = (world_id_a, world_id_b)
    
    return closest_pair[0], closest_pair[1], min_distance


def generate_planet(rng: random.Random, planet_type_data: Dict[str, Any], planet_names_data: Dict[str, List[str]]) -> Planet:
    """
    Generates a single planet based on provided planet type data and assigns a name.
    """
    # Sample habitability
    h_bands, h_weights = _process_weights_for_random_selection(planet_type_data["habitability_distribution"])
    selected_band = rng.choices(h_bands, weights=h_weights, k=1)[0]["band"]
    habitability = rng.uniform(selected_band[0], selected_band[1])

    # Choose resource table based on habitability
    selected_resource_table = None
    for table_name, table_data in planet_type_data["resource_tables"].items():
        is_gte_check = "when_habitability_gte" in table_data
        is_lt_check = "when_habitability_lt" in table_data

        if is_gte_check and habitability >= table_data["when_habitability_gte"]:
            selected_resource_table = table_data
            break
        elif is_lt_check and habitability < table_data["when_habitability_lt"]:
            selected_resource_table = table_data
            break
    
    if not selected_resource_table:
        # Default to a generic table if no thresholds met, or raise error
        selected_resource_table = list(planet_type_data["resource_tables"].values())[0]

    # Sample resource potentials
    resource_potentials: Dict[CommodityId, float] = {}
    for resource_id_str, potential_data in selected_resource_table["potentials"].items():
        potential_value = _sample_from_range_or_bins(rng, potential_data)
        resource_potentials[CommodityId(resource_id_str)] = potential_value

    # Assign a name to the planet
    planet_type_id = planet_type_data["id"]
    name = rng.choice(planet_names_data.get(planet_type_id, [f"{planet_type_id.capitalize()} Planet"]))


    return Planet(
        type=planet_type_id,
        name=name, # Assign the generated name
        habitability=habitability,
        resource_potentials=resource_potentials,
        tags=set() # Placeholder for planet-specific tags
    )


def generate_world(world_id_str: str, rng: random.Random, system_template_data: Dict[str, Any], planet_types_data: Dict[str, Any], planet_names_data: Dict[str, List[str]], system_names_data: List[str]) -> World:
    """
    Generates a World object for a given system, including its planets and a name from a list.
    """
    world_id = WorldId(world_id_str)
    world_name = rng.choice(system_names_data) # Assign a random system name

    min_planets = system_template_data["min_planets"]
    max_planets = system_template_data["max_planets"]
    num_planets = rng.randint(min_planets, max_planets)

    planets: List[Planet] = []
    planet_type_choices, planet_type_weights = _process_weights_for_random_selection(list(planet_types_data.values()))

    for _ in range(num_planets):
        selected_planet_type_data = rng.choices(planet_type_choices, weights=planet_type_weights, k=1)[0]
        planet = generate_planet(rng, selected_planet_type_data, planet_names_data) # Pass planet_names_data
        planets.append(planet)
    
    # Aggregate planet properties into world-level properties (rudimentary for now)
    # This will be expanded in Milestone 22

    # Generate x and y coordinates with a bias towards the center
    # Clamp values to stay within the defined range
    world_x = max(WORLD_COORD_RANGE_X[0], min(WORLD_COORD_RANGE_X[1], rng.gauss(WORLD_COORD_CENTER_X, WORLD_COORD_STD_DEV)))
    world_y = max(WORLD_COORD_RANGE_Y[0], min(WORLD_COORD_RANGE_Y[1], rng.gauss(WORLD_COORD_CENTER_Y, WORLD_COORD_STD_DEV)))

    world = World(
        id=world_id,
        name=world_name,
        planets=planets,
        stability=rng.uniform(0.5, 1.0), # Random initial stability
        prosperity=rng.uniform(0.5, 1.0), # Random initial prosperity
        tech=rng.uniform(0.5, 1.0), # Random initial tech
        tags=set(),
        x=world_x, # Assign biased X coordinate
        y=world_y  # Assign biased Y coordinate
    )
    return world

def generate_universe(rng: random.Random, n_systems: int, system_templates_data: Dict[str, Any], planet_types_data: Dict[str, Any], planet_names_data: Dict[str, List[str]], system_names_data: List[str], initial_state: Optional[UniverseState] = None) -> UniverseState:
    """
    Generates an entire UniverseState with N systems, potentially extending an initial state.
    """
    if initial_state:
        universe_state = initial_state
        universe_state.rng = rng # Ensure rng is updated if passed
    else:
        universe_state = UniverseState(seed=rng.randint(0, 2**32 - 1), rng=rng)
    
    # Placeholder: currently generates N worlds, each representing a system with planets
    # For now, use the 'default_system' template
    default_system_template = system_templates_data.get("default_system") # Use the passed argument
    if not default_system_template:
        raise ValueError("Default system template not found.")

    # Assign x, y coordinates to worlds from initial_state if not already present
    for world_id, world in universe_state.worlds.items():
        if world.x is None or world.y is None:
            world.x = max(WORLD_COORD_RANGE_X[0], min(WORLD_COORD_RANGE_X[1], rng.gauss(WORLD_COORD_CENTER_X, WORLD_COORD_STD_DEV)))
            world.y = max(WORLD_COORD_RANGE_Y[0], min(WORLD_COORD_RANGE_Y[1], rng.gauss(WORLD_COORD_CENTER_Y, WORLD_COORD_STD_DEV)))

    # Only add systems if they don't already exist (in case initial_state already has some worlds)
    existing_world_ids = set(universe_state.worlds.keys())
    for i in range(n_systems):
        world_id_str = f"sys-{i+1}"
        if WorldId(world_id_str) in existing_world_ids:
            continue # Skip if world already exists

        world = generate_world(world_id_str, rng, default_system_template, planet_types_data, planet_names_data, system_names_data) # Use passed arguments
        apply_planet_potentials_to_world(world, universe_state) # Apply bootstrap logic
        universe_state.worlds[world.id] = world
    
    # Lanes are generated separately by generate_non_intersecting_lanes, so remove logic here.

    return universe_state