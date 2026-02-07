from __future__ import annotations
from typing import TYPE_CHECKING
import random

from ..core.ids import RecipeId, CommodityId

if TYPE_CHECKING:
    from ..world.model import World
    from ..core.state import UniverseState


def invest_civilian(world: World, state: UniverseState):
    """
    Civilian investment consumes minerals to increase production caps for civilian recipes.
    """
    if not world.market or not world.industry:
        return

    minerals_needed = 10.0 # Example: 10 minerals per investment unit
    investment_units = 1.0 # For now, always 1 unit of investment per tick
    
    if world.market.inventory.get(CommodityId("minerals")) >= minerals_needed:
        world.market.inventory.remove_clamped(CommodityId("minerals"), minerals_needed)

        # Select a civilian industry to boost (farm_food, mine_minerals, refine_consumer_goods)
        civilian_recipes_candidates = [RecipeId("farm_food"), RecipeId("mine_minerals"), RecipeId("refine_consumer_goods")]
        
        # Filter for recipes that are actually in this world's industry caps
        available_civilian_recipes = [r_id for r_id in civilian_recipes_candidates if r_id in world.industry.caps]

        if available_civilian_recipes:
            target_recipe_id = state.rng.choice(available_civilian_recipes)
            world.industry.caps[target_recipe_id] += investment_units # Increase cap
        # else: No available civilian recipes to invest in


def invest_military(world: World, state: UniverseState):
    """
    Military investment consumes alloys to increase production caps for military recipes or garrison.
    """
    if not world.market or not world.industry:
        return

    alloys_needed = 5.0 # Example: 5 alloys per investment unit
    investment_units = 1.0 # For now, always 1 unit of investment per tick
    
    if world.market.inventory.get(CommodityId("alloy")) >= alloys_needed:
        world.market.inventory.remove_clamped(CommodityId("alloy"), alloys_needed)

        # Select a military industry to boost (refine_alloy, assemble_alloys)
        military_recipes_candidates = [RecipeId("refine_alloy"), RecipeId("assemble_alloys")]

        # Filter for recipes that are actually in this world's industry caps
        available_military_recipes = [r_id for r_id in military_recipes_candidates if r_id in world.industry.caps]

        if available_military_recipes:
            target_recipe_id = state.rng.choice(available_military_recipes)
            world.industry.caps[target_recipe_id] += investment_units # Increase cap
