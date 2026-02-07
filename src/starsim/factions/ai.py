from __future__ import annotations
from typing import TYPE_CHECKING, Dict

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

    # Geographic factors
    # Simple neighbor count
    neighbor_count = len(state.neighbors(world.id))
    score += neighbor_count * 2.0

    # Symbolic factors (from tags)
    if "capital" in world.tags:
        score += 50.0
    if "sacred" in world.tags:
        score += 30.0

    # Threat/Control factors
    if world.factions and world.factions.control == faction.id:
        score += 20.0 # Own world is more valuable

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

    # Consider expanding influence to neighboring worlds
    # For now, just pick the most valuable un-controlled neighbor
    for world_id, world in state.worlds.items():
        if world.factions and world.factions.control != faction.id:
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
