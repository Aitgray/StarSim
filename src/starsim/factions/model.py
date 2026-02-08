from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set, TYPE_CHECKING, Optional
from collections import defaultdict # Added defaultdict import

from ..core.ids import FactionId, WorldId, CommodityId # Added CommodityId

if TYPE_CHECKING:
    from ..world.model import World


@dataclass
class Faction:
    id: FactionId
    name: str
    color: str = "#CCCCCC" # New: Default color for the faction
    traits: Set[str] = field(default_factory=set)
    # Weights for various decisions or influences (e.g., preference for certain commodity types)
    weights: Dict[str, float] = field(default_factory=dict)
    capital_world_id: Optional[WorldId] = None # New: The ID of this faction's capital system
    resource_desire: float = 0.5 # New: Scalar representing a general desire for resources (e.g., 0.0 to 1.0)


@dataclass
class WorldFactionState:
    """
    Represents the state of factions within a specific world.
    This would be part of UniverseState.
    """
    # Influence of each faction in this world (0.0 to 1.0)
    influence: Dict[FactionId, float] = field(default_factory=lambda: defaultdict(float))
    # Garrison strength of each faction in this world (raw numbers)
    garrison: Dict[FactionId, float] = field(default_factory=lambda: defaultdict(float))
    # Who controls this world (derived, can be None if contested)
    control: Optional[FactionId] = None 

    # Hysteresis parameters for control changes
    control_threshold_gain: float = 0.7
    control_threshold_loss: float = 0.4
    
    def resolve_control(self):
        """
        Determines which faction controls the world based on influence, with hysteresis.
        """
        if not self.influence:
            self.control = None
            return

        # Find the faction with the highest influence
        current_dominant_faction = max(self.influence, key=self.influence.get)
        highest_influence = self.influence[current_dominant_faction]

        # Check if there's a clear dominant faction
        # (e.g., highest influence > some threshold above others)
        # For simplicity, let's just consider the highest for now.
        
        if self.control is None:
            # No current control, assign if a faction has high influence
            if highest_influence >= self.control_threshold_gain:
                self.control = current_dominant_faction
        elif self.control == current_dominant_faction:
            # Current controller is still dominant, retain control
            pass
        else:
            # A different faction is dominant, check if current controller loses influence
            # or if new dominant faction gains enough
            if highest_influence >= self.control_threshold_gain and \
               self.influence.get(self.control, 0.0) < self.control_threshold_loss:
                self.control = current_dominant_faction
            # If current controller's influence is still above threshold_loss
            # even if not dominant, they might retain control due to hysteresis.
            # This logic needs refinement based on specific game design.
