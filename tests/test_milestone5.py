import pytest
from pathlib import Path

from src.starsim.core.ids import WorldId, CommodityId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry, Commodity
from src.starsim.economy.inventory import Inventory
from src.starsim.economy.market import Market, update_prices
from src.starsim.economy.consumption import Population, consume
from src.starsim.world.load import load_universe
from src.starsim.world.model import World
from src.starsim.core.sim import step


@pytest.fixture(autouse=True)
def setup_commodities():
    # Ensure commodity registry is loaded before tests
    if not commodity_registry._commodities:
        commodity_registry.load_from_yaml(Path("data/commodities.yaml"))


@pytest.fixture
def world_with_population_and_market() -> World:
    world = World(id=WorldId("test_pop_world"), name="Test Pop World")
    
    market = Market()
    market.inventory.add(CommodityId("food"), 100.0) # Some initial food
    market.prices[CommodityId("food")] = commodity_registry.get(CommodityId("food")).base_price
    world.market = market

    population = Population(size=1_000, needs={CommodityId("food"): 0.1}) # Needs 100 food per tick
    world.population = population
    
    world.stability = 0.8
    world.unrest = 0.2
    world.scarcity = 0.0
    
    return world


@pytest.fixture
def universe_state_for_consumption(world_with_population_and_market) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_population_and_market.id] = world_with_population_and_market
    return state


def test_consumption_removes_from_inventory(universe_state_for_consumption):
    world = universe_state_for_consumption.worlds[WorldId("test_pop_world")]
    initial_food_in_market = world.market.inventory.get(CommodityId("food"))
    
    consume(world, universe_state_for_consumption.tick)
    
    expected_consumed = world.population.size * world.population.needs[CommodityId("food")]
    assert world.market.inventory.get(CommodityId("food")) == pytest.approx(initial_food_in_market - expected_consumed)


def test_shortage_ratio_calculation_insufficient_inventory(universe_state_for_consumption):
    world = universe_state_for_consumption.worlds[WorldId("test_pop_world")]
    world.market.inventory[CommodityId("food")] = 50.0 # Not enough for 100 population need
    
    initial_stability = world.stability
    initial_unrest = world.unrest
    initial_scarcity = world.scarcity

    consume(world, universe_state_for_consumption.tick)

    # Expected shortage_ratio for food: (100 - 50) / 100 = 0.5
    # Since 0.5 > 0.1, instability should increase
    assert world.stability < initial_stability
    assert world.unrest > initial_unrest
    assert world.scarcity > initial_scarcity
    
    # Test bounds
    assert 0.0 <= world.stability <= 1.0
    assert 0.0 <= world.unrest <= 1.0
    assert 0.0 <= world.scarcity <= 1.0


def test_shortage_ratio_calculation_sufficient_inventory(universe_state_for_consumption):
    world = universe_state_for_consumption.worlds[WorldId("test_pop_world")]
    world.market.inventory[CommodityId("food")] = 200.0 # More than enough
    
    initial_stability = world.stability
    initial_unrest = world.unrest
    initial_scarcity = world.scarcity

    consume(world, universe_state_for_consumption.tick)
    
    assert world.stability == initial_stability
    assert world.unrest == initial_unrest
    assert world.scarcity == initial_scarcity


def test_two_ticks_no_food_worsens_instability_deterministically():
    # Setup two identical states
    state1 = UniverseState(seed=42)
    world1 = World(id=WorldId("w1"), name="World 1")
    market1 = Market()
    market1.inventory[CommodityId("food")] = 10.0 # Small amount
    world1.market = market1
    population1 = Population(size=100, needs={CommodityId("food"): 1.0}) # Needs 100 food
    world1.population = population1
    world1.stability = 0.8
    world1.unrest = 0.2
    world1.scarcity = 0.0
    state1.worlds[WorldId("w1")] = world1

    state2 = UniverseState(seed=42) # Same seed
    world2 = World(id=WorldId("w1"), name="World 1")
    market2 = Market()
    market2.inventory[CommodityId("food")] = 10.0 # Small amount
    world2.market = market2
    population2 = Population(size=100, needs={CommodityId("food"): 1.0}) # Needs 100 food
    world2.population = population2
    world2.stability = 0.8
    world2.unrest = 0.2
    world2.scarcity = 0.0
    state2.worlds[WorldId("w1")] = world2

    # Simulate first tick
    step(state1)
    step(state2)

    assert state1.worlds[WorldId("w1")].stability == pytest.approx(state2.worlds[WorldId("w1")].stability)
    assert state1.worlds[WorldId("w1")].unrest == pytest.approx(state2.worlds[WorldId("w1")].unrest)
    assert state1.worlds[WorldId("w1")].scarcity == pytest.approx(state2.worlds[WorldId("w1")].scarcity)

    # Store values after first tick
    stability_after_first_tick = state1.worlds[WorldId("w1")].stability
    unrest_after_first_tick = state1.worlds[WorldId("w1")].unrest
    scarcity_after_first_tick = state1.worlds[WorldId("w1")].scarcity

    # Instability should worsen
    assert stability_after_first_tick < 0.8
    assert unrest_after_first_tick > 0.2
    assert scarcity_after_first_tick > 0.0

    # Simulate second tick
    step(state1)
    step(state2)

    assert state1.worlds[WorldId("w1")].stability == pytest.approx(state2.worlds[WorldId("w1")].stability)
    assert state1.worlds[WorldId("w1")].unrest == pytest.approx(state2.worlds[WorldId("w1")].unrest)
    assert state1.worlds[WorldId("w1")].scarcity == pytest.approx(state2.worlds[WorldId("w1")].scarcity)

    # Instability should worsen further
    assert state1.worlds[WorldId("w1")].stability < stability_after_first_tick
    assert state1.worlds[WorldId("w1")].unrest > unrest_after_first_tick
    assert state1.worlds[WorldId("w1")].scarcity > scarcity_after_first_tick
