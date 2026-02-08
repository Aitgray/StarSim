from __future__ import annotations
from typing import TYPE_CHECKING, Dict
import math # Import math for sqrt
from ..core.ids import CommodityId # Import CommodityId

if TYPE_CHECKING:
    from ..core.state import UniverseState
    from ..world.model import World
    from .model import Faction, FactionId


def compute_world_value(faction: Faction, world: World, state: UniverseState) -> float:
    """
    Computes a value score for a world from a faction's perspective.
    This is a highly simplified placeholder.
    """
    score = 0.0

    # Economic factors
    if world.market:
        # Simple heuristic: worlds with more food or minerals are valuable
        score += world.market.inventory.get(CommodityId("food"), 0.0) * 0.01
        score += world.market.inventory.get(CommodityId("minerals"), 0.0) * 0.005
    if world.industry:
        # Worlds with production capabilities are valuable
        score += len(world.industry.caps) * 10.0 # Each recipe cap adds value

    # Resource prioritization based on faction's general desire and planet potentials
    if world.planets and faction.resource_desire > 0:
        total_planet_potential = 0.0
        for planet in world.planets:
            for potential_value in planet.resource_potentials.values():
                total_planet_potential += potential_value
        score += total_planet_potential * faction.resource_desire * 0.5 # Scale by resource_desire and a constant

    # Trait-based resource bias
    if "expansionist" in faction.traits:
        # Expansionist factions value food and minerals more
        if world.planets:
            for planet in world.planets:
                score += planet.resource_potentials.get(CommodityId("food"), 0.0) * 2.0
                score += planet.resource_potentials.get(CommodityId("minerals"), 0.0) * 1.5
    
    if "aggressive" in faction.traits:
        # Aggressive factions value alloy and energy more
        if world.planets:
            for planet in world.planets:
                score += planet.resource_potentials.get(CommodityId("alloy"), 0.0) * 2.5
                score += planet.resource_potentials.get(CommodityId("energy"), 0.0) * 1.0

    # Geographic factors
    # Simple neighbor count
    neighbor_count = len(state.neighbors(world.id))
    score += neighbor_count * 2.0

    # Proximity to Capital (if defined)
    if faction.capital_world_id and faction.capital_world_id in state.worlds and world.id != faction.capital_world_id:
        capital_world = state.worlds[faction.capital_world_id]
        distance = math.sqrt((world.x - capital_world.x)**2 + (world.y - capital_world.y)**2)
        # Invert distance so closer worlds have higher score
        score += max(0, (100 - distance) * 0.1) # Scale and ensure non-negative

    # World Stability and Prosperity
    score += world.stability * 5.0
    score += world.prosperity * 5.0

    # Planet Count
    score += len(world.planets) * 2.0

    # Symbolic factors (from tags)
    if "capital" in world.tags:
        score += 50.0
    if "sacred" in world.tags:
        score += 30.0

    # Threat/Control factors
    if world.factions:
        if world.factions.control == faction.id:
            score += 20.0 # Own world is more valuable
        elif world.factions.control is None:
            score += 10.0 # Uncontested worlds are valuable for expansion
        elif world.factions.control != faction.id:
            # World is controlled by another faction, reduce its value for expansion
            score -= 5.0
            # Also consider influence by other factions, not just control
            if faction.id in world.factions.influence:
                score += world.factions.influence[faction.id] * 5.0 # Our influence makes it slightly more valuable
            for other_fac_id, influence in world.factions.influence.items():
                if other_fac_id != faction.id and other_fac_id == world.factions.control: # Opposing control
                    score -= influence * 10.0 # Significantly reduce value if strong opposing control

    # Instability/unrest decreases value
    score -= world.unrest * 10.0
    score -= world.scarcity * 5.0
    score -= (1.0 - world.stability) * 15.0

    return score


def select_action(faction: Faction, state: UniverseState) -> Dict[str, Any]:
    """
    Selects an action for the faction based on world values and current state.
    This is a greedy, simplified selection.
    """
    best_action = {"type": "no_action", "target": None, "score": -float('inf')}

    # Find all worlds currently controlled by this faction
    controlled_worlds = [w_id for w_id, w in state.worlds.items() if w.factions and w.factions.control == faction.id]

    # Collect all direct neighbors of controlled worlds that are not yet controlled by this faction
    candidate_expansion_worlds = set()
    for controlled_w_id in controlled_worlds:
        for neighbor_w_id in state.neighbors(controlled_w_id):
            neighbor_world = state.worlds[neighbor_w_id]
            # Only consider worlds not controlled by this faction
            if not neighbor_world.factions or neighbor_world.factions.control != faction.id:
                candidate_expansion_worlds.add(neighbor_w_id)

    # Evaluate candidate expansion worlds
    for world_id in candidate_expansion_worlds:
        world = state.worlds[world_id]
        value = compute_world_value(faction, world, state)
        if value > best_action["score"]:
            best_action = {"type": "expand_influence", "target": world.id, "score": value}
    
    # Consider civilian investment
    if faction.traits and "expansionist" in faction.traits: # Example heuristic
        for world_id, world in state.worlds.items():
            if world.factions and world.factions.control == faction.id: # Owned world
                # Check if we have enough minerals for civilian investment
                if world.market and world.market.inventory.get(CommodityId("minerals")) >= 10.0:
                    # Score for civilian investment could be tied to current industry efficiency or needs
                    score = world.prosperity * 10.0 + (1.0 - world.scarcity) * 5.0
                    if score > best_action["score"]:
                        best_action = {"type": "invest_civilian", "target": world.id, "score": score}

    # Consider military investment
    if faction.traits and "aggressive" in faction.traits: # Example heuristic
        for world_id, world in state.worlds.items():
            if world.factions and world.factions.control == faction.id: # Owned world
                # Check if we have enough alloys for military investment
                if world.market and world.market.inventory.get(CommodityId("alloy")) >= 5.0:
                    # Score for military investment could be tied to nearby threats or unrest
                    score = world.unrest * 10.0 + (1.0 - world.stability) * 5.0
                    if score > best_action["score"]:
                        best_action = {"type": "invest_military", "target": world.id, "score": score}

    return best_action


def select_action_debug(faction: Faction, state: UniverseState) -> Dict[str, Any]:
    """
    Debug version of select_action that prints world values and selected action.
    """
    world_values = {}
    for world_id, world in state.worlds.items():
        value = compute_world_value(faction, world, state)
        world_values[world_id] = value

    debug_output = {
        "faction_id": faction.id,
        "world_values": world_values,
        "selected_action": select_action(faction, state),
    }
    return debug_output
