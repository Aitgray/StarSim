from __future__ import annotations
from typing import TYPE_CHECKING
import math

from ..core.ids import CommodityId

if TYPE_CHECKING:
    from ..world.model import World
    from ..core.state import UniverseState


def apply_upkeep(world: World, state: UniverseState):
    """
    Applies energy upkeep costs and penalties for energy deficit.
    """
    if not world.market or not world.population or not world.industry:
        return

    population = world.population
    market = world.market
    industry = world.industry

    # Calculate energy upkeep for population
    population_upkeep = population.size * population.energy_upkeep_per_capita_per_tick

    # Calculate infrastructure upkeep (simple: based on total industry caps)
    infrastructure_upkeep = sum(industry.caps.values()) * 0.1 # 0.1 energy per cap unit

    total_energy_upkeep = population_upkeep + infrastructure_upkeep
    
    # Consume energy
    actual_energy_consumed = market.inventory.remove_clamped(CommodityId("energy"), total_energy_upkeep)
    energy_deficit = total_energy_upkeep - actual_energy_consumed
    
    if energy_deficit > 0:
        # Apply penalties for energy deficit
        deficit_ratio = energy_deficit / total_energy_upkeep if total_energy_upkeep > 0 else 0.0

        # Reduce stability and prosperity
        world.stability = max(0.0, world.stability - deficit_ratio * 0.05)
        world.prosperity = max(0.0, world.prosperity - deficit_ratio * 0.05)
        
        # Throttle production caps (e.g., reduce by deficit ratio)
        for recipe_id in industry.caps.keys():
            industry.caps[recipe_id] = max(0.0, industry.caps[recipe_id] * (1.0 - deficit_ratio * 0.1)) # 10% reduction
