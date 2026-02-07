import pytest
from pathlib import Path

from src.starsim.core.ids import WorldId, CommodityId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.market import Market
from src.starsim.economy.consumption import Population, consume
from src.starsim.world.model import World


@pytest.fixture(autouse=True)
def setup_commodities():
    if not commodity_registry._commodities:
        commodity_registry.load_from_yaml(Path("data/commodities.yaml"))


@pytest.fixture
def world_with_population() -> World:
    world = World(id=WorldId("test_pop_world"), name="Test Population World")
    market = Market()
    market.inventory.add(CommodityId("food"), 0.0) # Initially no food
    world.market = market

    population = Population(
        size=1000,
        growth_rate=0.01, # 1% growth
        needs={CommodityId("food"): 0.0001}, # 0.0001 food per capita
        food_required_per_capita_per_tick=0.0001
    )
    world.population = population
    world.stability = 1.0
    world.prosperity = 1.0
    
    return world


@pytest.fixture
def universe_state_for_pop(world_with_population) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_population.id] = world_with_population
    return state


def test_insufficient_food_decreases_population(universe_state_for_pop):
    world = universe_state_for_pop.worlds[WorldId("test_pop_world")]
    initial_pop_size = world.population.size
    
    # Ensure no food is available
    world.market.inventory[CommodityId("food")] = 0.0
    
    consume(world, universe_state_for_pop.tick)
    
    # Population should decline
    assert world.population.size < initial_pop_size
    assert world.population.size == 950 # 1000 * (1 - 1*0.05)


def test_sufficient_food_increases_population(universe_state_for_pop):
    world = universe_state_for_pop.worlds[WorldId("test_pop_world")]
    initial_pop_size = world.population.size
    
    # Provide abundant food
    world.market.inventory.add(CommodityId("food"), 1000.0) # More than enough for 1000 pop * 0.0001 food/capita = 0.1 food
    
    consume(world, universe_state_for_pop.tick)
    
    # Population should increase (1000 * (1 + 0.01 * (1.0+1.0)/2)) = 1000 * (1 + 0.01) = 1010
    assert world.population.size > initial_pop_size
    assert world.population.size == 1010


def test_food_shortage_impacts_pressures(universe_state_for_pop):
    world = universe_state_for_pop.worlds[WorldId("test_pop_world")]
    
    # Ensure no food is available
    world.market.inventory[CommodityId("food")] = 0.0
    
    initial_stability = world.stability
    initial_unrest = world.unrest
    initial_scarcity = world.scarcity
    
    consume(world, universe_state_for_pop.tick)
    
    # Scarcity, unrest should increase, stability should decrease
    assert world.scarcity > initial_scarcity
    assert world.unrest > initial_unrest
    assert world.stability < initial_stability
    
    # Check bounds
    assert 0.0 <= world.stability <= 1.0
    assert 0.0 <= world.unrest <= 1.0
    assert 0.0 <= world.scarcity <= 1.0
    assert world.starvation_level > 0.0
    assert world.food_balance < 0.0
