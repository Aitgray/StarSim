from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Set, List, TYPE_CHECKING # Import List

from ..core.ids import WorldId, LaneId, FactionId # Import FactionId
from ..economy.market import Market # Import Market
from ..generation.model import Planet # Import Planet

if TYPE_CHECKING:
    from ..economy.consumption import Population # Forward reference
    from ..economy.production import Industry # Forward reference
    from ..factions.model import WorldFactionState # Forward reference


@dataclass
class World:
    id: WorldId
    name: str
    stability: float = 1.0
    prosperity: float = 1.0
    tech: float = 1.0
    tags: Set[str] = field(default_factory=set)
    x: float = 0.0 # New: X coordinate for visualization/distance calculations
    y: float = 0.0 # New: Y coordinate for visualization/distance calculations

    # World-level pressures
    scarcity: float = 0.0
    unrest: float = 0.0
    food_balance: float = 0.0 # New: food surplus/deficit
    starvation_level: float = 0.0 # New: how severe the food shortage is
    consumer_goods_balance: float = 0.0 # New: consumer goods surplus/deficit
    consumer_goods_shortage_level: float = 0.0 # New: how severe the consumer goods shortage is

    # Planet-level data (for generated worlds)
    planets: List[Planet] = field(default_factory=list)

    # Optional components
    market: Optional[Market] = None
    population: Optional["Population"] = None
    industry: Optional["Industry"] = None
    factions: Optional["WorldFactionState"] = None # Add factions component
    control: Optional[FactionId] = None # Derived from factions.control


@dataclass
class Lane:
    id: LaneId
    a: WorldId
    b: WorldId
    distance: float = 1.0
    hazard: float = 0.0
    capacity: float = 1.0
