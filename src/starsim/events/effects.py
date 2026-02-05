from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from ..core.state import UniverseState
    from ..core.ids import WorldId, LaneId
    from ..world.model import World
    from ..economy.market import Market


def apply_effect(effect: Dict[str, Any], world: World, state: UniverseState):
    """Applies a single event effect to the world or other entities."""
    effect_type = effect["type"]

    if effect_type == "change_stability":
        delta = effect.get("delta", 0.0)
        world.stability = max(0.0, min(1.0, world.stability + delta))
    elif effect_type == "change_prosperity":
        delta = effect.get("delta", 0.0)
        world.prosperity = max(0.0, min(1.0, world.prosperity + delta))
    elif effect_type == "change_unrest":
        delta = effect.get("delta", 0.0)
        world.unrest = max(0.0, min(1.0, world.unrest + delta))
    elif effect_type == "change_scarcity": # Not currently used by events, but good to have
        delta = effect.get("delta", 0.0)
        world.scarcity = max(0.0, min(1.0, world.scarcity + delta))
    elif effect_type == "add_inventory":
        if world.market:
            commodity_id = effect["commodity_id"]
            quantity = effect["quantity"]
            world.market.inventory.add(commodity_id, quantity)
    elif effect_type == "remove_inventory":
        if world.market:
            commodity_id = effect["commodity_id"]
            quantity = effect["quantity"]
            world.market.inventory.remove_clamped(commodity_id, quantity)
    elif effect_type == "change_lane_hazard":
        lane_id = effect.get("lane_id")
        delta = effect.get("delta", 0.0)
        
        if lane_id:
            lane = state.lanes.get(LaneId(lane_id))
        else:
            # If no specific lane_id, choose a random lane connected to the world
            connected_lanes = state.lanes_from(world.id)
            if connected_lanes:
                lane = state.rng.choice(connected_lanes)
            else:
                lane = None # No connected lanes to affect

        if lane:
            lane.hazard = max(0.0, min(1.0, lane.hazard + delta))
    elif effect_type == "remove_inventory_random_worlds":
        commodity_id = effect["commodity_id"]
        quantity_per_world = effect["quantity"]
        num_worlds = effect["num_worlds"]

        # Select random worlds
        target_world_ids = state.rng.sample(list(state.worlds.keys()), min(num_worlds, len(state.worlds)))
        for target_world_id in target_world_ids:
            target_world = state.worlds[target_world_id]
            if target_world.market:
                target_world.market.inventory.remove_clamped(commodity_id, quantity_per_world)
    # TODO: Add faction influence shifts, capacity modifiers etc.
