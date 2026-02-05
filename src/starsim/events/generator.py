from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any
import random

if TYPE_CHECKING:
    from ..core.state import UniverseState
    from ..core.ids import WorldId
    from ..world.model import World
    from ..economy.market import Market
    from .model import EventDef # Keep this for type hinting in EventDef in evaluate_event_conditions


def evaluate_event_conditions(event_def: EventDef, world: World, state: UniverseState) -> float:
    """
    Evaluates an event's conditions against a world's state to determine
    a weight multiplier. Returns 1.0 if no conditions, or if conditions are met.
    """
    multiplier = 1.0
    for condition in event_def.conditions:
        condition_type = condition["type"]
        weight_multiplier = condition.get("weight_multiplier", 1.0)
        condition_met = False

        if condition_type == "world_unrest":
            if world.unrest >= condition.get("min", 0.0) and \
               world.unrest <= condition.get("max", 1.0):
                multiplier *= weight_multiplier
                condition_met = True
        elif condition_type == "world_scarcity":
            # For simplicity, if any commodity has scarcity, condition is met
            if world.scarcity >= condition.get("min", 0.0) and \
               world.scarcity <= condition.get("max", 1.0):
                multiplier *= weight_multiplier
                condition_met = True
        elif condition_type == "world_tag":
            if condition["tag"] in world.tags:
                multiplier *= weight_multiplier
                condition_met = True
        elif condition_type == "world_tech":
            if world.tech >= condition.get("min", 0.0) and \
               world.tech <= condition.get("max", 1.0):
                multiplier *= weight_multiplier
                condition_met = True
        elif condition_type == "lane_hazard":
            # This condition needs to be evaluated for lanes connected to the world
            # For simplicity, let's assume any connected lane's hazard can trigger it
            for lane in state.lanes_from(world.id):
                if lane.hazard >= condition.get("min", 0.0) and \
                   lane.hazard <= condition.get("max", 1.0):
                    multiplier *= weight_multiplier
                    condition_met = True
                    break # Only need one lane to meet condition
        # TODO: Add more complex conditions like faction tension, etc.

    return multiplier


def generate_events(state: UniverseState, max_events_per_tick: int = 1) -> List[tuple[EventDef, WorldId]]:
    """
    Generates a list of events for the current tick based on world states and event weights.
    """
    possible_events_with_weights: List[tuple[EventDef, WorldId, float]] = []

    for world_id, world in state.worlds.items():
        for event_def in state.event_registry.all_events():
            weight_multiplier = evaluate_event_conditions(event_def, world, state)
            final_weight = event_def.base_weight * weight_multiplier
            if final_weight > 0:
                possible_events_with_weights.append((event_def, world_id, final_weight))

    # Normalize weights and select events
    if not possible_events_with_weights:
        return []

    # Simple selection: pick highest weighted events, or random weighted selection
    # For now, let's do weighted random selection
    selected_events: List[tuple[EventDef, WorldId]] = []
    
    # Extract weights for random.choices
    events_only = [item for item in possible_events_with_weights]
    weights = [item[2] for item in possible_events_with_weights] # The third element is the weight
    
    # Use random.choices for weighted random selection
    # `k` specifies number of events to pick
    if weights and sum(weights) > 0: # Ensure there are positive weights to choose from
        chosen_events = state.rng.choices(
            events_only,
            weights=weights,
            k=min(max_events_per_tick, len(events_only))
        )
        selected_events = [(event_def, world_id) for event_def, world_id, _ in chosen_events]

    return selected_events
