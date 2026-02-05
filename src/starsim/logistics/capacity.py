from dataclasses import dataclass, field
from typing import Dict
from collections import defaultdict

from ..core.ids import LaneId


@dataclass
class LaneCapacity:
    # Tracks used capacity for current tick
    # Reset each tick during trade phase (or similar)
    used_capacity: Dict[LaneId, float] = field(default_factory=lambda: defaultdict(float))

    def add_used_capacity(self, lane_id: LaneId, quantity: float):
        self.used_capacity[lane_id] += quantity

    def get_remaining_capacity(self, lane_id: LaneId, total_capacity: float) -> float:
        return max(0.0, total_capacity - self.used_capacity[lane_id])

    def reset(self):
        self.used_capacity.clear()
