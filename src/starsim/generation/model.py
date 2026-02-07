from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.ids import CommodityId


@dataclass
class Planet:
    type: str # e.g., "continental", "desert", "ocean"
    habitability: float # 0.0 to 1.0
    resource_potentials: Dict[CommodityId, float] = field(default_factory=dict) # e.g., {"minerals": 5.0, "food": 3.0}
    tags: Set[str] = field(default_factory=set) # e.g., "volcanic", "rich_ore"
