from dataclasses import dataclass
from typing import Optional

from ..core.ids import CommodityId, WorldId


@dataclass
class Shipment:
    commodity_id: CommodityId
    quantity: float
    source_world_id: WorldId
    destination_world_id: WorldId
    eta_tick: int # Estimated Time of Arrival (tick number)
    lane_id: Optional[str] = None # For tracking which lane it's on
