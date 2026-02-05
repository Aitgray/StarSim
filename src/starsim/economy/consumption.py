from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING

from ..core.ids import CommodityId
from .inventory import Inventory

if TYPE_CHECKING:
    from ..world.model import World


@dataclass
class Population:
    size: int = 1_000_000
    growth_rate: float = 0.01 # 1% growth per tick
    needs: Dict[CommodityId, float] = field(default_factory=dict) # qty per capita per tick


def consume(world: "World", tick: int):
    """
    Population consumes from the market inventory according to its needs.
    Computes shortage ratios.
    """
    if not world.population or not world.market:
        return

    population = world.population
    market = world.market

    # Initialize pressure fields if they don't exist
    if not hasattr(world, 'scarcity'):
        world.scarcity = 0.0
    if not hasattr(world, 'unrest'):
        world.unrest = 0.0

    shortage_ratios: Dict[CommodityId, float] = {}

    for commodity_id, need_per_capita in population.needs.items():
        needed_qty = need_per_capita * population.size
        print(f"DEBUG_CONSUME:   Needed Qty for {commodity_id}: {needed_qty:.2f}")
        print(f"DEBUG_CONSUME:   Market Inventory for {commodity_id} before consumption: {market.inventory.get(commodity_id):.2f}")
        
        # Consume from market
        actual_consumed = market.inventory.remove_clamped(commodity_id, needed_qty)
        print(f"DEBUG_CONSUME:   Actual Consumed for {commodity_id}: {actual_consumed:.2f}")
        
        if needed_qty > 0:
            shortage_ratio = (needed_qty - actual_consumed) / needed_qty
        else:
            shortage_ratio = 0.0 # No need, no shortage
        
        shortage_ratios[commodity_id] = shortage_ratio

        # --- Shortage-driven instability (placeholder) ---
        print(f"DEBUG_CONSUME: World {world.id}, Commodity {commodity_id}, Shortage Ratio: {shortage_ratio:.2f}")
        print(f"DEBUG_CONSUME: Initial stability: {world.stability:.2f}, unrest: {world.unrest:.2f}, scarcity: {world.scarcity:.2f}")

        if shortage_ratio > 0.1: # Significant shortage
            world.scarcity = min(1.0, world.scarcity + shortage_ratio * 0.01) # Increase scarcity pressure
            # Decrease stability, bounded
            world.stability = max(0.0, world.stability - shortage_ratio * 0.05)
            # Increase unrest, bounded
            world.unrest = min(1.0, world.unrest + shortage_ratio * 0.05)
            print(f"DEBUG_CONSUME: After adjustment - stability: {world.stability:.2f}, unrest: {world.unrest:.2f}, scarcity: {world.scarcity:.2f}")
