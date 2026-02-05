from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .ids import WorldId, FactionId


@dataclass
class AuditEntry:
    type: str
    tick: int
    world_id: Optional[WorldId] = None
    faction_id: Optional[FactionId] = None
    delta: float = 0.0
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLog:
    def __init__(self):
        self.entries: List[AuditEntry] = []

    def add_entry(
        self,
        type: str,
        tick: int,
        world_id: Optional[WorldId] = None,
        faction_id: Optional[FactionId] = None,
        delta: float = 0.0,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        entry = AuditEntry(
            type=type,
            tick=tick,
            world_id=world_id,
            faction_id=faction_id,
            delta=delta,
            reason=reason,
            details=details or {},
        )
        self.entries.append(entry)
