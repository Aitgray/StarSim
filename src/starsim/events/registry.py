from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any
import yaml

from .model import EventDef


class EventRegistry:
    def __init__(self):
        self._events: Dict[str, EventDef] = {}

    def load_from_yaml(self, path: Path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        if data is None:
            raise ValueError(f"YAML file '{path}' is empty or malformed.")
        
        for e_data in data:
            event_def = EventDef(
                id=e_data['id'],
                base_weight=e_data.get('base_weight', 1.0),
                conditions=e_data.get('conditions', []),
                effects=e_data.get('effects', [])
            )
            self._events[event_def.id] = event_def

    def get(self, event_id: str) -> EventDef:
        if event_id not in self._events:
            raise ValueError(f"Event with ID '{event_id}' not found.")
        return self._events[event_id]

    def all_events(self) -> List[EventDef]:
        return list(self._events.values())

# Global registry instance
event_registry = EventRegistry()