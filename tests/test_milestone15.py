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
def world_with_pop_and_market_cg() -> World:
    world = World(id=WorldId("test_cg_world"), name="Test CG World")
    
    market = Market()
    market.inventory.add(CommodityId("consumer_goods"), 0.0) # Initially no CG
    market.inventory.add(CommodityId("food"), 1000.0) # Add sufficient food to avoid food shortages
    world.market = market

    population = Population(
        size=1000,
        consumer_goods_required_per_capita_per_tick=0.01, # Needs 10 CG (changed from 0.1)
        consumer_goods_excess_burn_rate=0.5
    )
    world.population = population
    world.stability = 0.5
    world.prosperity = 0.5
    world.unrest = 0.5
    
    return world


@pytest.fixture
def universe_state_for_cg(world_with_pop_and_market_cg) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_pop_and_market_cg.id] = world_with_pop_and_market_cg
    return state


def test_cg_shortage_reduces_stability_prosperity_increases_unrest(universe_state_for_cg):
    world = universe_state_for_cg.worlds[WorldId("test_cg_world")]
    initial_stability = world.stability
    initial_prosperity = world.prosperity
    initial_unrest = world.unrest
    
    # Ensure CG shortage
    world.market.inventory[CommodityId("consumer_goods")] = 0.0
    
    consume(world, universe_state_for_cg.tick)
    
    # Stability and prosperity should decrease, unrest should increase
    assert world.stability < initial_stability
    assert world.prosperity < initial_prosperity
    assert world.unrest > initial_unrest
    assert world.consumer_goods_shortage_level > 0.0
    assert world.consumer_goods_balance < 0.0
    
    # Check bounds
    assert 0.0 <= world.stability <= 1.0
    assert 0.0 <= world.prosperity <= 1.0
    assert 0.0 <= world.unrest <= 1.0


def test_cg_surplus_increases_stability_burns_excess(universe_state_for_cg):
    world = universe_state_for_cg.worlds[WorldId("test_cg_world")]
    initial_stability = world.stability
    
    # Provide abundant CG
    world.market.inventory.add(CommodityId("consumer_goods"), 500.0) # More than needed
    initial_cg_in_market = world.market.inventory.get(CommodityId("consumer_goods"))
    
    # Calculate expected consumed CG
    total_cg_needed = world.population.size * world.population.consumer_goods_required_per_capita_per_tick
    
    consume(world, universe_state_for_cg.tick)
    
    # Stability should increase
    assert world.stability > initial_stability
    assert world.consumer_goods_shortage_level == 0.0
    assert world.consumer_goods_balance >= 0.0 # Can be 0 if exact consumption
    
    # Check for excess burn: initial - consumed - remaining in market
    remaining_in_market = world.market.inventory.get(CommodityId("consumer_goods"))
    total_consumed_and_burned = initial_cg_in_market - remaining_in_market
    
    # Expected total consumed + burned: total_cg_needed + (initial_cg_in_market - total_cg_needed) * burn_rate
    # If initial = 500, needed = 10, burn_rate = 0.5
    # Actual consumed = 10. Excess = 490. Burned = 490 * 0.5 = 245. Total removed = 10 + 245 = 255. Remaining = 245.
    
    expected_burned = (initial_cg_in_market - total_cg_needed) * world.population.consumer_goods_excess_burn_rate
    
    actual_cg_consumed = total_cg_needed
    excess_after_consumption = initial_cg_in_market - actual_cg_consumed
    expected_final_inventory = excess_after_consumption - (excess_after_consumption * world.population.consumer_goods_excess_burn_rate)
    
    assert remaining_in_market == pytest.approx(expected_final_inventory, abs=1e-1)