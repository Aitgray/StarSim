import pytest
from pathlib import Path

from src.starsim.core.ids import WorldId, CommodityId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry, Commodity
from src.starsim.economy.inventory import Inventory
from src.starsim.economy.market import Market, update_prices
from src.starsim.world.load import load_universe
from src.starsim.world.model import World
from src.starsim.core.sim import step


@pytest.fixture(autouse=True)
def setup_commodities():
    # Ensure commodity registry is loaded before tests
    # This might have been loaded by UniverseState already in previous tests,
    # but explicit load here for safety
    if not commodity_registry._commodities:
        commodity_registry.load_from_yaml(Path("data/commodities.yaml"))


@pytest.fixture
def test_world_with_market() -> World:
    # Create a world with a market for testing price updates
    world = World(id=WorldId("test_market_world"), name="Test Market World")
    market = Market()
    
    # Set initial inventory for testing
    market.inventory.add(CommodityId("food"), 50.0)
    market.inventory.add(CommodityId("ore"), 100.0)

    # Set initial prices (e.g., base price)
    food_commodity = commodity_registry.get(CommodityId("food"))
    ore_commodity = commodity_registry.get(CommodityId("ore"))
    market.prices[food_commodity.id] = food_commodity.base_price
    market.prices[ore_commodity.id] = ore_commodity.base_price

    # Set targets
    market.targets[CommodityId("food")] = 100.0 # Target more than current inventory
    market.targets[CommodityId("ore")] = 50.0  # Target less than current inventory
    
    world.market = market
    return world


@pytest.fixture
def universe_state_with_market(test_world_with_market) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[test_world_with_market.id] = test_world_with_market
    return state


def test_price_increases_when_inventory_below_target(universe_state_with_market):
    world = universe_state_with_market.worlds[WorldId("test_market_world")]
    market = world.market
    
    initial_food_price = market.prices[CommodityId("food")]
    
    # Food inventory (50) is below target (100)
    update_prices(world, universe_state_with_market)
    
    assert market.prices[CommodityId("food")] > initial_food_price


def test_price_decreases_when_inventory_above_target(universe_state_with_market):
    world = universe_state_with_market.worlds[WorldId("test_market_world")]
    market = world.market
    
    initial_ore_price = market.prices[CommodityId("ore")]
    
    # Ore inventory (100) is above target (50)
    update_prices(world, universe_state_with_market)
    
    assert market.prices[CommodityId("ore")] < initial_ore_price


def test_price_remains_within_bounds(universe_state_with_market):
    world = universe_state_with_market.worlds[WorldId("test_market_world")]
    market = world.market

    food_commodity = commodity_registry.get(CommodityId("food"))
    ore_commodity = commodity_registry.get(CommodityId("ore"))

    # Force prices to extremes to test clamping
    market.prices[food_commodity.id] = food_commodity.base_price * 0.1 # Below min bound
    market.prices[ore_commodity.id] = ore_commodity.base_price * 5.0 # Above max bound

    for _ in range(5): # Run several updates to ensure clamping
        update_prices(world, universe_state_with_market)

    min_food_price = food_commodity.base_price * market.min_price_multiplier
    max_food_price = food_commodity.base_price * market.max_price_multiplier
    min_ore_price = ore_commodity.base_price * market.min_price_multiplier
    max_ore_price = ore_commodity.base_price * market.max_price_multiplier

    assert min_food_price <= market.prices[food_commodity.id] <= max_food_price
    assert min_ore_price <= market.prices[ore_commodity.id] <= max_ore_price


def test_world_with_missing_prices_sets_defaults_without_crash(universe_yaml_path):
    # Load universe with market defined in YAML (sol world)
    state = load_universe(universe_yaml_path)
    sol_world = state.worlds[WorldId("sol")]
    assert sol_world.market is not None
    
    # Ensure some prices are missing to test default setting (e.g., for a new commodity if added later)
    # For now, let's assume 'tools' might not be explicitly set in universe.yaml for sol
    if CommodityId("tools") not in sol_world.market.prices:
        sol_world.market.prices.pop(CommodityId("tools"), None) # Ensure it's not there

    # Update prices - should set default for 'tools' if not present
    update_prices(sol_world, state)
    
    tools_commodity = commodity_registry.get(CommodityId("tools"))
    assert tools_commodity.id in sol_world.market.prices
    assert sol_world.market.prices[tools_commodity.id] >= tools_commodity.base_price * sol_world.market.min_price_multiplier


def test_simulation_step_with_market_updates_prices(universe_yaml_path):
    # Load state directly from YAML, which now includes market data for 'sol'
    state = load_universe(universe_yaml_path)
    sol_world = state.worlds[WorldId("sol")]
    
    # Capture initial prices for sol's market
    initial_food_price = sol_world.market.prices.get(CommodityId("food"))
    initial_ore_price = sol_world.market.prices.get(CommodityId("ore"))

    # Perform one simulation step
    report = step(state)
    
    # Check if prices have changed (expect food price to increase, ore to decrease based on universe.yaml)
    # Note: The gazette will contain detailed log entries if changes occurred
    food_entry_found = False
    ore_entry_found = False
    for entry in report.log.entries:
        if entry.type == "economy.prices.update" and entry.world_id == sol_world.id:
            if entry.details.get("commodity_id") == CommodityId("food"):
                food_entry_found = True
            if entry.details.get("commodity_id") == CommodityId("ore"):
                ore_entry_found = True

    assert sol_world.market.prices[CommodityId("food")] < initial_food_price
    assert sol_world.market.prices[CommodityId("ore")] < initial_ore_price
    assert food_entry_found
    assert ore_entry_found
