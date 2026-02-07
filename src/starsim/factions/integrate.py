from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from ..core.state import UniverseState
    from ..core.ids import FactionId, WorldId, LaneId
    from .model import Faction
    from .ai import select_action
    from .actions import expand_influence, reinforce, raid_lane, patrol_lane, aid_world, invest_civilian_action, invest_military_action


def apply_faction_actions(state: UniverseState):
    """
    Factions select and apply actions to the universe state.
    """
    # For now, a very simple loop where each faction gets to act
    # In a more complex simulation, this would involve turn order,
    # resource expenditure, and more sophisticated AI.

    for faction_id, faction in state.factions.items():
        # Faction AI decides on an action
        action_plan = select_action(faction, state)
        action_type = action_plan["type"]
        target_id = action_plan["target"]

        success = False
        if action_type == "expand_influence" and target_id:
            success = expand_influence(faction_id, WorldId(target_id), state)
        elif action_type == "reinforce" and target_id:
            success = reinforce(faction_id, WorldId(target_id), state)
        elif action_type == "raid_lane" and target_id:
            success = raid_lane(faction_id, LaneId(target_id), state)
        elif action_type == "patrol_lane" and target_id:
            success = patrol_lane(faction_id, LaneId(target_id), state)
        elif action_type == "aid_world" and target_id:
            success = aid_world(faction_id, WorldId(target_id), state)
        elif action_type == "invest_civilian" and target_id:
            success = invest_civilian_action(faction_id, WorldId(target_id), state)
        elif action_type == "invest_military" and target_id:
            success = invest_military_action(faction_id, WorldId(target_id), state)
        
        # Log the action
        if success:
            # TODO: More detailed logging of action effects
            pass
