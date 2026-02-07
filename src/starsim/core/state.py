import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

from .ids import WorldId, LaneId, FactionId # Import FactionId
from .rng import get_seeded_rng
from ..world.model import World, Lane
from ..economy.commodities import CommodityRegistry, commodity_registry # Import commodity_registry
from ..economy.recipes import RecipeRegistry, recipe_registry # Import RecipeRegistry and recipe_registry
from ..logistics.shipping import Shipment # Import Shipment
from ..logistics.capacity import LaneCapacity # Import LaneCapacity
from ..factions.model import Faction # Import Faction
from ..events.registry import EventRegistry, event_registry # Import EventRegistry and event_registry


@dataclass
class UniverseState:
    seed: int
    tick: int = 0
    rng: random.Random = field(default=None, init=True) # Allow passing an existing RNG
    worlds: Dict[WorldId, World] = field(default_factory=dict)
    lanes: Dict[LaneId, Lane] = field(default_factory=dict)
    
    commodity_registry: CommodityRegistry = field(default_factory=lambda: commodity_registry)
    recipe_registry: RecipeRegistry = field(default_factory=lambda: recipe_registry)
    event_registry: EventRegistry = field(default_factory=lambda: event_registry)
    factions: Dict[FactionId, Faction] = field(default_factory=dict) # Add faction registry
    active_shipments: List[Shipment] = field(default_factory=list) # Add active shipments list
    lane_capacity_tracker: LaneCapacity = field(default_factory=LaneCapacity) # Add lane capacity tracker

    # Derived adjacency list, will be rebuilt
    _adj: Dict[WorldId, List[LaneId]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        if self.rng is None:
            self.rng = get_seeded_rng(self.seed)
        self.rebuild_adjacency()


    def rebuild_adjacency(self):
        self._adj = {world_id: [] for world_id in self.worlds}
        for lane_id, lane in self.lanes.items():
            if lane.a in self._adj:
                self._adj[lane.a].append(lane_id)
            if lane.b in self._adj:
                self._adj[lane.b].append(lane_id)

    def neighbors(self, world_id: WorldId) -> List[WorldId]:
        neighbor_ids = []
        for lane_id in self._adj.get(world_id, []):
            lane = self.lanes[lane_id]
            if lane.a == world_id:
                neighbor_ids.append(lane.b)
            else:
                neighbor_ids.append(lane.a)
        return neighbor_ids

    def lanes_from(self, world_id: WorldId) -> List[Lane]:
        return [self.lanes[lane_id] for lane_id in self._adj.get(world_id, [])]
