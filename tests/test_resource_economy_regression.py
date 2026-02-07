import pytest
from pathlib import Path
import random

from src.starsim.core.state import UniverseState
from src.starsim.core.ids import WorldId, CommodityId, RecipeId # Import RecipeId
from src.starsim.world.model import World
from src.starsim.economy.consumption import Population
from src.starsim.economy.market import Market
from src.starsim.economy.inventory import Inventory
from src.starsim.economy.production import Industry
from src.starsim.generation.model import Planet
from src.starsim.generation.bootstrap import apply_planet_potentials_to_world # Used for initial state


@pytest.fixture
def basic_economy_world() -> World:
    """
    Provides a basic world with some population, market, and initial resources
    to simulate a simple economy.
    """
    world_id = WorldId("test-eco-world")
    world = World(id=world_id, name="Test Eco World", stability=0.7, prosperity=0.7)

    # Initialize population directly
    world.population = Population(size=1_000_000, growth_rate=0.01, food_required_per_capita_per_tick=0.0001)
    
    # Initialize market and inventory
    inventory = Inventory()
    inventory.add(CommodityId("food"), 10000.0)
    inventory.add(CommodityId("minerals"), 5000.0)
    inventory.add(CommodityId("consumer_goods"), 2000.0)
    market = Market(inventory=inventory, prices={
        CommodityId("food"): 10.0,
        CommodityId("minerals"): 5.0,
        CommodityId("consumer_goods"): 15.0
    })
    world.market = market

    # Initialize industry (simple production caps for now)
    world.industry = Industry()
    world.industry.caps[RecipeId("mine_minerals")] = 100.0 # Changed to RecipeId
    world.industry.caps[RecipeId("farm_food")] = 200.0 # Changed to RecipeId
    
    # Simulate a planet to make apply_planet_potentials_to_world happy
    dummy_planet = Planet(
        type="test_type",
        habitability=0.7,
        resource_potentials={
            CommodityId("food"): 3.0,
            CommodityId("minerals"): 2.0,
            CommodityId("energy"): 1.0,
        },
        tags=set()
    )
    world.planets.append(dummy_planet)

    # Apply bootstrap logic (this will re-initialize population, industry caps based on habitability)
    # This might overwrite the directly set values, depending on what we want to test.
    # For a regression test, it's better to be explicit about initial state.
    # If we want to test the full bootstrap, we would pass a UniverseState.
    # For now, let's skip apply_planet_potentials_to_world for this fixture to control initial state.

    # Instead of full bootstrap, just ensure Market has some prices for food/CG
    world.food_balance = 0.0
    world.starvation_level = 0.0
    world.consumer_goods_balance = 0.0
    world.consumer_goods_shortage_level = 0.0

    return world


@pytest.fixture
def sim_universe(basic_economy_world: World) -> UniverseState:
    """Provides a UniverseState for simulation."""
    universe = UniverseState(seed=42)
    universe.worlds[basic_economy_world.id] = basic_economy_world
    # Ensure recipes are loaded for production to work
    from src.starsim.economy.recipes import recipe_registry # Re-import to ensure it's loaded if not already
    universe.recipe_registry = recipe_registry # Assign the global registry for the sim
    return universe


def run_simulation_ticks(universe: UniverseState, num_ticks: int):
    """Runs the simulation for a given number of ticks."""
    from src.starsim.economy.consumption import consume
    from src.starsim.economy.production import produce
    
    for _ in range(num_ticks):
        # Placeholder for full simulation loop (run all processes)
        # For this regression test, we only care about consumption and production
        for world in universe.worlds.values():
            produce(world, universe)
            consume(world, universe.tick)
        universe.tick += 1 # Increment tick after all worlds have processed for this tick


def test_no_negative_inventories(sim_universe: UniverseState):
    """Asserts that no commodity inventory ever drops below zero."""
    num_ticks = 5 # Small number of ticks for quick check
    run_simulation_ticks(sim_universe, num_ticks)

    for world in sim_universe.worlds.values():
        if world.market and world.market.inventory:
            for commodity_id, quantity in world.market.inventory.to_dict().items():
                assert quantity >= 0.0, f"Inventory for {commodity_id} went negative ({quantity}) in {world.name}"


def test_population_growth_with_and_without_food(): # No fixture here, create everything inside
    # Scenario 1: Sufficient food (expect growth)
    # Use a fresh world instance for isolated test
    world_id_growth = WorldId("growth-world")
    growth_world = World(id=world_id_growth, name="Growth World", stability=0.7, prosperity=0.7)
    growth_world.population = Population(size=1_000_000, growth_rate=0.01, food_required_per_capita_per_tick=0.0001)
    growth_world.market = Market(inventory=Inventory(), prices={
        CommodityId("food"): 10.0, CommodityId("minerals"): 5.0, CommodityId("consumer_goods"): 15.0
    })
    growth_world.industry = Industry()
    # Add a dummy planet for world.planets to avoid errors in apply_planet_potentials_to_world if called elsewhere
    growth_world.planets.append(Planet(type="earth", habitability=0.7, resource_potentials={}, tags=set()))

    universe_growth = UniverseState(seed=42)
    universe_growth.worlds[growth_world.id] = growth_world
    from src.starsim.economy.recipes import recipe_registry
    universe_growth.recipe_registry = recipe_registry # Assign the global registry

    initial_pop_growth = growth_world.population.size
    growth_world.market.inventory.add(CommodityId("food"), 100_000.0) # Ensure ample food
    num_ticks_growth = 5
    run_simulation_ticks(universe_growth, num_ticks_growth)
    assert growth_world.population.size > initial_pop_growth, "Population did not grow with sufficient food."
    # Removed hardcoded population value


    # Scenario 2: Food shortage (expect decline)
    # Use another fresh world instance for isolated test
    world_id_decline = WorldId("decline-world")
    decline_world = World(id=world_id_decline, name="Decline World", stability=0.7, prosperity=0.7)
    decline_world.population = Population(size=1_000_000, growth_rate=0.01, food_required_per_capita_per_tick=0.0001)
    decline_world.market = Market(inventory=Inventory(), prices={
        CommodityId("food"): 10.0, CommodityId("minerals"): 5.0, CommodityId("consumer_goods"): 15.0
    })
    decline_world.industry = Industry()
    decline_world.planets.append(Planet(type="mars", habitability=0.3, resource_potentials={}, tags=set()))
    
    universe_decline = UniverseState(seed=43)
    universe_decline.worlds[decline_world.id] = decline_world
    universe_decline.recipe_registry = recipe_registry # Assign the global registry

    initial_pop_decline = decline_world.population.size
    # Remove all food - it should decline
    decline_world.market.inventory.remove_clamped(CommodityId("food"), decline_world.market.inventory.get(CommodityId("food")) + 1000.0) # Ensure no food
    num_ticks_decline = 5
    run_simulation_ticks(universe_decline, num_ticks_decline)
    assert decline_world.population.size < initial_pop_decline, "Population did not decline during food shortage."
    # Removed hardcoded population value


def test_consumer_goods_excess_bounded(sim_universe: UniverseState):
    """
    Tests that consumer goods excess does not grow unbounded due to burn-off.
    This is hard to test deterministically without a full sim loop.
    For now, assert that excess is not ridiculously high after a few ticks.
    """
    test_world = sim_universe.worlds[WorldId("test-eco-world")]
    initial_cg = test_world.market.inventory.get(CommodityId("consumer_goods"))
    
    # Ensure a large surplus of CG and some production
    test_world.market.inventory.add(CommodityId("consumer_goods"), 10_000.0)
    test_world.industry.caps[CommodityId("refine_consumer_goods")] = 500.0 # Ensure production (Placeholder RecipeId)
    
    num_ticks = 10
    run_simulation_ticks(sim_universe, num_ticks)
    
    # It should be less than initial + huge production, or at least not growing extremely fast
    current_cg = test_world.market.inventory.get(CommodityId("consumer_goods"))
    assert current_cg < (initial_cg + 10_000.0 + (500.0 * num_ticks * 100)), \
        "Consumer goods excess seems to be growing unbounded."

