from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING
import math # Import math for ceil and floor

from ..core.ids import CommodityId
from .inventory import Inventory

if TYPE_CHECKING:
    from ..world.model import World


@dataclass
class Population:
    size: int = 1_000_000
    growth_rate: float = 0.01 # Base growth rate per tick (e.g., 1% growth per tick)
    needs: Dict[CommodityId, float] = field(default_factory=dict) # qty per capita per tick (e.g., food: 0.0001)
    
    # New fields for Milestone 14
    food_required_per_capita_per_tick: float = 0.0001 # Explicit rate for food

    # New fields for Milestone 15
    consumer_goods_required_per_capita_per_tick: float = 0.0001
    consumer_goods_excess_burn_rate: float = 0.5 # 50% of excess consumer goods are "burned off"

    # New fields for Milestone 18
    energy_upkeep_per_capita_per_tick: float = 0.0001


def consume(world: "World", tick: int):
    """
    Population consumes from the market inventory according to its needs.
    Computes shortage ratios and applies population changes.
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
    if not hasattr(world, 'food_balance'):
        world.food_balance = 0.0
    if not hasattr(world, 'starvation_level'):
        world.starvation_level = 0.0
    if not hasattr(world, 'consumer_goods_balance'):
        world.consumer_goods_balance = 0.0
    if not hasattr(world, 'consumer_goods_shortage_level'):
        world.consumer_goods_shortage_level = 0.0

    shortage_ratios: Dict[CommodityId, float] = {}

    # --- Food Consumption (Milestone 14) ---
    total_food_needed = population.size * population.food_required_per_capita_per_tick
    food_available = market.inventory.get(CommodityId("food"))

    if total_food_needed > 0:
        actual_food_consumed = market.inventory.remove_clamped(CommodityId("food"), total_food_needed)
        food_shortage = total_food_needed - actual_food_consumed
        food_shortage_ratio = food_shortage / total_food_needed
    else:
        actual_food_consumed = 0.0
        food_shortage = 0.0
        food_shortage_ratio = 0.0

    world.food_balance = actual_food_consumed - total_food_needed
    world.starvation_level = food_shortage_ratio

    # Apply population changes based on food
    if food_shortage_ratio > 0:
        decline_factor = food_shortage_ratio * 0.05
        population.size = max(0, math.floor(population.size * (1.0 - decline_factor)))
    else:
        if population.size > 0:
            growth_multiplier = (world.stability + world.prosperity) / 2.0
            growth_amount = population.size * population.growth_rate * growth_multiplier
            population.size = math.floor(population.size * (1.0 + growth_amount / population.size))
    
    # Update world unrest and scarcity based on food shortage
    world.scarcity = min(1.0, world.scarcity + food_shortage_ratio * 0.02)
    world.unrest = min(1.0, world.unrest + food_shortage_ratio * 0.03)
    world.stability = max(0.0, world.stability - food_shortage_ratio * 0.04)

    # --- Consumer Goods Consumption (Milestone 15) ---
    total_cg_needed = population.size * population.consumer_goods_required_per_capita_per_tick
    cg_available = market.inventory.get(CommodityId("consumer_goods"))

    if total_cg_needed > 0:
        actual_cg_consumed = market.inventory.remove_clamped(CommodityId("consumer_goods"), total_cg_needed)
        cg_shortage = total_cg_needed - actual_cg_consumed
        cg_shortage_ratio = cg_shortage / total_cg_needed
    else:
        actual_cg_consumed = 0.0
        cg_shortage = 0.0
        cg_shortage_ratio = 0.0
    
    world.consumer_goods_balance = actual_cg_consumed - total_cg_needed
    world.consumer_goods_shortage_level = cg_shortage_ratio

    if cg_shortage_ratio > 0:
        # Penalties for consumer goods shortage
        world.stability = max(0.0, world.stability - cg_shortage_ratio * 0.02) # Mild stability reduction
        world.prosperity = max(0.0, world.prosperity - cg_shortage_ratio * 0.01) # Mild prosperity reduction
        world.unrest = min(1.0, world.unrest + cg_shortage_ratio * 0.01) # Mild unrest increase
    else:
        # Bonus for consumer goods surplus
        # Calculate actual excess in inventory after consumption
        # cg_available was the amount before consumption, now subtract the actual_cg_consumed
        excess_in_market_after_consumption = cg_available - actual_cg_consumed
        
        if excess_in_market_after_consumption > 0 and population.size > 0:
            cg_excess_per_capita = excess_in_market_after_consumption / population.size
            stability_bonus = cg_excess_per_capita * 100.0 * 0.005 # Example: 0.005 stability bonus per 100 excess CG per capita
            world.stability = min(1.0, world.stability + stability_bonus)

            # Burn off excess consumer goods (from what's left in the market after consumption)
            burn_amount = excess_in_market_after_consumption * population.consumer_goods_excess_burn_rate
            market.inventory.remove_clamped(CommodityId("consumer_goods"), burn_amount)

    # --- Other commodity consumption (if any) ---
    for commodity_id, need_per_capita in population.needs.items():
        if commodity_id == CommodityId("food") or commodity_id == CommodityId("consumer_goods"): # Already handled
            continue

        needed_qty = need_per_capita * population.size
        actual_consumed = market.inventory.remove_clamped(commodity_id, needed_qty)
        
        if needed_qty > 0:
            shortage_ratio = (needed_qty - actual_consumed) / needed_qty
        else:
            shortage_ratio = 0.0
        
        shortage_ratios[commodity_id] = shortage_ratio

        if shortage_ratio > 0.1: # Significant shortage for other commodities
            world.scarcity = min(1.0, world.scarcity + shortage_ratio * 0.01)
            world.stability = max(0.0, world.stability - shortage_ratio * 0.05)
            world.unrest = min(1.0, world.unrest + shortage_ratio * 0.05)
