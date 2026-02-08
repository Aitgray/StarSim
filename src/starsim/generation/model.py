from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.ids import CommodityId


@dataclass
class Planet:
    type: str # e.g., "continental", "desert", "ocean"
    name: str = "" # New: Individual name of the planet
    habitability: float = 0.0 # 0.0 to 1.0, added default to resolve TypeError
    resource_potentials: Dict[CommodityId, float] = field(default_factory=dict) # e.g., {"minerals": 5.0, "food": 3.0}
    tags: Set[str] = field(default_factory=set) # e.g., "volcanic", "rich_ore"
