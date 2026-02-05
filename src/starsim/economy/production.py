from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, TYPE_CHECKING

from ..core.ids import RecipeId, CommodityId
from ..world.model import World
from .recipes import Recipe

if TYPE_CHECKING:
    from ..core.state import UniverseState


@dataclass
class Industry:
    caps: Dict[RecipeId, float] = field(default_factory=dict) # max output per tick for each recipe


def produce(world: World, state: UniverseState):
    """
    World industries consume inputs and produce outputs based on available resources and capacities.
    """
    if not world.market or not world.industry:
        return

    market = world.market
    industry = world.industry

    for recipe_id, cap_amount in industry.caps.items():
        recipe = state.recipe_registry.get(recipe_id)
        
        max_possible_by_inputs = float('inf')
        # Determine max production based on inputs
        for input_id, input_qty_per_unit in recipe.inputs.items():
            if input_qty_per_unit > 0:
                available_input = market.inventory.get(input_id)
                max_possible_by_inputs = min(max_possible_by_inputs, available_input / input_qty_per_unit)
        
        # Determine actual production units, limited by capacity, industry cap, and inputs
        production_units = min(cap_amount, recipe.max_production_units_per_tick, max_possible_by_inputs)
        
        if production_units > 0:
            # Consume inputs
            for input_id, input_qty_per_unit in recipe.inputs.items():
                market.inventory.remove_clamped(input_id, input_qty_per_unit * production_units)
            
            # Add outputs
            for output_id, output_qty_per_unit in recipe.outputs.items():
                market.inventory.add(output_id, output_qty_per_unit * production_units)
