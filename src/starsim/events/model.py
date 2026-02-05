from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class EventDef:
    id: str
    base_weight: float = 1.0
    # Conditions are a list of dictionaries, e.g., [{"type": "world_unrest", "min": 0.5, "weight_multiplier": 2.0}]
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    # Effects are a list of dictionaries, e.g., [{"type": "change_stability", "world_id": "$target_world", "delta": -0.1}]
    effects: List[Dict[str, Any]] = field(default_factory=list)
