from typing import Dict
from collections import defaultdict

from ..core.ids import CommodityId


class Inventory:
    def __init__(self):
        self._quantities: Dict[CommodityId, float] = defaultdict(float)

    def get(self, commodity_id: CommodityId, default_qty: float = 0.0) -> float:
        """Returns the quantity of a commodity, or a default if not present."""
        return self._quantities.get(commodity_id, default_qty)

    def add(self, commodity_id: CommodityId, quantity: float):
        """Adds a quantity of a commodity to the inventory."""
        if quantity < 0:
            raise ValueError("Quantity to add must be non-negative.")
        self._quantities[commodity_id] += quantity

    def remove_clamped(self, commodity_id: CommodityId, quantity: float) -> float:
        """
        Removes a quantity of a commodity, clamping at zero.
        Returns the actual amount removed.
        """
        if quantity < 0:
            raise ValueError("Quantity to remove must be non-negative.")
        
        current_qty = self._quantities[commodity_id]
        actual_removed = min(quantity, current_qty)
        self._quantities[commodity_id] -= actual_removed
        if self._quantities[commodity_id] < 1e-9: # Avoid tiny floating point negatives
            del self._quantities[commodity_id]
        return actual_removed

    def __getitem__(self, commodity_id: CommodityId) -> float:
        return self.get(commodity_id)

    def __setitem__(self, commodity_id: CommodityId, quantity: float):
        if quantity < 0:
            raise ValueError("Inventory quantity cannot be negative.")
        self._quantities[commodity_id] = quantity
        if quantity < 1e-9: # Clean up zero entries
            del self._quantities[commodity_id]

    def to_dict(self) -> Dict[CommodityId, float]:
        return dict(self._quantities)
