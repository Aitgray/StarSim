from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, TYPE_CHECKING

from ..core.ids import WorldId, CommodityId
from .inventory import Inventory

if TYPE_CHECKING:
    from ..core.state import UniverseState
    from ..world.model import World


@dataclass
class Market:
    inventory: Inventory = field(default_factory=Inventory)
    prices: Dict[CommodityId, float] = field(default_factory=dict)
    targets: Dict[CommodityId, float] = field(default_factory=dict) # days-of-cover target

    # Price adjustment parameters
    price_change_factor: float = 0.1 # How much prices react
    min_price_multiplier: float = 0.5
    max_price_multiplier: float = 2.0


def update_prices(world: "World", state: "UniverseState"):
    """
    Adjusts prices based on inventory levels compared to targets.
    """
    if not world.market:
        return

    market = world.market
    
    # Ensure all commodities have a target and initial price
    for commodity in state.commodity_registry.all_commodities():
        if commodity.id not in market.targets:
            # Default target to 10 days of cover, for now just a fixed number
            # This should eventually be driven by population needs or other factors
            market.targets[commodity.id] = 10.0 
        if commodity.id not in market.prices:
            market.prices[commodity.id] = commodity.base_price

    for commodity_id, target_qty in market.targets.items():
        current_qty = market.inventory.get(commodity_id)
        current_price = market.prices.get(commodity_id, state.commodity_registry.get(commodity_id).base_price)

        print(f"DEBUG: {world.id} - Commodity: {commodity_id}")
        print(f"DEBUG:   Current Qty: {current_qty}, Target Qty: {target_qty}")
        print(f"DEBUG:   Current Price: {current_price}")

        # Simple heuristic: if inventory < target, price increases; if > target, price decreases
        # The larger the difference, the larger the change
        if target_qty > 0: # Avoid division by zero
            ratio = current_qty / target_qty
        else: # If target is zero, any inventory is surplus
            ratio = 10.0 # Arbitrarily high to reduce price
        print(f"DEBUG:   Ratio (current_qty / target_qty): {ratio}")

        # Adjust price based on ratio
        # If ratio < 1, price increases. If ratio > 1, price decreases.
        # price_change_factor determines the speed of adjustment
        price_adjustment = (1.0 - ratio) * market.price_change_factor
        new_price = current_price * (1.0 + price_adjustment)
        print(f"DEBUG:   Price Adjustment: {price_adjustment}")
        print(f"DEBUG:   New Price (before clamp): {new_price}")

        # Clamp price within bounds
        base_price = state.commodity_registry.get(commodity_id).base_price
        min_bound = base_price * market.min_price_multiplier
        max_bound = base_price * market.max_price_multiplier
        print(f"DEBUG:   Base Price: {base_price}, Min Bound: {min_bound}, Max Bound: {max_bound}")
        
        market.prices[commodity_id] = max(min_bound, min(max_bound, new_price))
        print(f"DEBUG:   Final Price: {market.prices[commodity_id]}")
