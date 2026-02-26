from __future__ import annotations
from typing import TYPE_CHECKING
from math import floor

from ..core.ids import CommodityId, RecipeId # Import RecipeId
from ..economy.consumption import Population
from ..economy.production import Industry
from ..economy.market import Market
from ..factions.model import WorldFactionState

if TYPE_CHECKING:
    from ..world.model import World
    from ..core.state import UniverseState # Added UniverseState for type hinting

# Constants for Milestone 22
BASE_POPULATION = 1_000_000
PRODUCTION_CAP_SCALING_FACTOR = 100.0


def apply_planet_potentials_to_world(world: "World", universe_state: "UniverseState" = None):
    """
    Applies generated planet potentials to a world's starting state.

    Args:
        world: The world object to modify.
        universe_state: The current universe state (for accessing global data if needed).
    """
    if world.population is None:
        world.population = Population()
    if world.industry is None:
        world.industry = Industry()
    if world.market is None:
        world.market = Market()
    if world.factions is None:
        world.factions = WorldFactionState()

    # Apply habitability impacts as per Milestone 22 rules
    if world.planets:
        primary_planet = world.planets[0]

        # Base stability/prosperity from habitability
        world.stability = primary_planet.habitability
        world.prosperity = primary_planet.habitability

        # Set default population size based on habitability
        # Ensure a minimum population of 1
        world.population.size = max(1, floor(BASE_POPULATION * primary_planet.habitability))

        # Map potentials to industry caps
        # Initialize caps if they haven't been (Industry default_factory might already do this)
        if not world.industry.caps:
            world.industry.caps = {}

        for commodity_id, potential_value in primary_planet.resource_potentials.items():
            scaled_cap = potential_value * PRODUCTION_CAP_SCALING_FACTOR

            if commodity_id == CommodityId("minerals"):
                world.industry.caps[RecipeId("mine_minerals")] = scaled_cap
            elif commodity_id == CommodityId("food"):
                world.industry.caps[RecipeId("farm_food")] = scaled_cap
            elif commodity_id == CommodityId("energy"):
                # Temporary: Energy potential slightly boosts food and mineral production capacity
                # A more robust energy production system would have its own recipe.
                world.industry.caps.setdefault(RecipeId("farm_food"), 0.0)
                world.industry.caps[RecipeId("farm_food")] += scaled_cap * 0.5
                world.industry.caps.setdefault(RecipeId("mine_minerals"), 0.0)
                world.industry.caps[RecipeId("mine_minerals")] += scaled_cap * 0.5

        # TODO: Implement population growth cap, effective output multiplier
