from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.ids import FactionId, WorldId, LaneId
    from ..core.state import UniverseState
    from ..world.model import World
    from .model import Faction


def expand_influence(faction_id: FactionId, world_id: WorldId, state: UniverseState) -> bool:
    """
    Attempts to expand faction influence in a target world.
    (Placeholder: directly increases influence)
    """
    world = state.worlds.get(world_id)
    if world and world.factions:
        world.factions.influence[faction_id] += 0.1
        world.factions.resolve_control()
        return True
    return False


def reinforce(faction_id: FactionId, world_id: WorldId, state: UniverseState) -> bool:
    """
    Sends reinforcements to a world, increasing garrison.
    (Placeholder: directly increases garrison)
    """
    world = state.worlds.get(world_id)
    if world and world.factions:
        world.factions.garrison[faction_id] += 10.0
        return True
    return False


def raid_lane(faction_id: FactionId, lane_id: LaneId, state: UniverseState) -> bool:
    """
    Attempts to raid a lane, increasing its hazard.
    (Placeholder: directly increases lane hazard)
    """
    lane = state.lanes.get(lane_id)
    if lane:
        lane.hazard = min(1.0, lane.hazard + 0.1)
        return True
    return False


def patrol_lane(faction_id: FactionId, lane_id: LaneId, state: UniverseState) -> bool:
    """
    Patrols a lane, decreasing its hazard.
    (Placeholder: directly decreases lane hazard)
    """
    lane = state.lanes.get(lane_id)
    if lane:
        lane.hazard = max(0.0, lane.hazard - 0.05)
        return True
    return False


def aid_world(faction_id: FactionId, world_id: WorldId, state: UniverseState) -> bool:
    """
    Provides aid to a world, increasing its stability and prosperity.
    (Placeholder: directly increases stability and prosperity)
    """
    world = state.worlds.get(world_id)
    if world:
        world.stability = min(1.0, world.stability + 0.05)
        world.prosperity = min(1.0, world.prosperity + 0.05)
        return True
    return False
