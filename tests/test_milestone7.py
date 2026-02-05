import pytest
from pathlib import Path
from copy import deepcopy

from src.starsim.core.ids import WorldId, LaneId, CommodityId, RecipeId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.inventory import Inventory
from src.starsim.economy.market import Market, update_prices
from src.starsim.economy.consumption import Population, consume
from src.starsim.economy.recipes import recipe_registry, Recipe
from src.starsim.economy.production import Industry, produce
from src.starsim.economy.trade import build_candidate_trades, process_trade
from src.starsim.world.load import load_universe
from src.starsim.world.model import World, Lane
from src.starsim.core.sim import step
from src.starsim.logistics.shipping import Shipment
from src.starsim.logistics.capacity import LaneCapacity


@pytest.fixture(autouse=True)
def setup_registries():
    if not commodity_registry._commodities:
        commodity_registry.load_from_yaml(Path("data/commodities.yaml"))
    if not recipe_registry._recipes:
        recipe_registry.load_from_yaml(Path("data/recipes.yaml"))


@pytest.fixture
def two_world_trade_state() -> UniverseState:
    state = UniverseState(seed=123)

    # World 1: Source of food, low price (low inventory means price should rise)
    world1_id = WorldId("w1")
    world1 = World(id=world1_id, name="World 1")
    market1 = Market()
    market1.inventory.add(CommodityId("food"), 5.0) # Low food inventory
    market1.prices[CommodityId("food")] = 8.0 # Low food price
    world1.market = market1
    state.worlds[world1_id] = world1

    # World 2: Destination for food, high price (large inventory means price should fall)
    world2_id = WorldId("w2")
    world2 = World(id=world2_id, name="World 2")
    market2 = Market(min_price_multiplier=0.9) # Increase min price multiplier
    market2.inventory.add(CommodityId("food"), 50.0) # Large food inventory
    market2.prices[CommodityId("food")] = 15.0 # High food price
    world2.market = market2
    state.worlds[world2_id] = world2

    # Lane connecting them
    lane_id = LaneId("l1-2")
    lane = Lane(id=lane_id, a=world1_id, b=world2_id, distance=1.0, hazard=0.0, capacity=100.0)
    state.lanes[lane_id] = lane

    state.rebuild_adjacency()
    yield state # Yield the state to the test

    # Teardown: clear active shipments and capacity tracker after test runs
    state.active_shipments.clear()
    state.lane_capacity_tracker.reset()


def test_profitable_trades_create_shipments(two_world_trade_state):
    state = two_world_trade_state
    
    # Ensure a profitable trade exists (food from w1 to w2)
    # price_b (15) - price_a (8) - shipping_cost > TRADE_THRESHOLD (0.1)
    # shipping_cost for food = 10.0 * (1.0 * 0.01 + 0.0 * 0.05) = 0.1
    # profit = 15 - 8 - 0.1 = 6.9 > 0.1
    candidates = build_candidate_trades(state)
    
    assert len(candidates) == 1
    shipment = candidates[0]
    assert shipment.commodity_id == CommodityId("food")
    assert shipment.source_world_id == WorldId("w1")
    assert shipment.destination_world_id == WorldId("w2")
    assert shipment.quantity == 5.0 # Limited by available inventory


def test_shipments_arrive_after_travel_time(two_world_trade_state):
    state = two_world_trade_state
    state.active_shipments.clear() # Clear any existing shipments from fixture setup
    
    # Create a shipment
    test_shipment = Shipment(
        commodity_id=CommodityId("food"),
        quantity=5.0,
        source_world_id=WorldId("w1"),
        destination_world_id=WorldId("w2"),
        eta_tick=state.tick + 2, # Arrives in 2 ticks
        lane_id=LaneId("l1-2"),
    )
    state.active_shipments.append(test_shipment)
    
    initial_w2_food = state.worlds[WorldId("w2")].market.inventory.get(CommodityId("food"))
    
    # Simulate one tick - shipment should not arrive yet
    state.tick += 1
    arrived = process_trade(state, allow_new_trades=False)
    assert len(arrived) == 0
    assert len(state.active_shipments) == 1
    assert state.worlds[WorldId("w2")].market.inventory.get(CommodityId("food")) == initial_w2_food

    # Simulate another tick - shipment should arrive
    state.tick += 1
    arrived = process_trade(state, allow_new_trades=False)
    assert len(arrived) == 1
    assert len(state.active_shipments) == 0
    assert state.worlds[WorldId("w2")].market.inventory.get(CommodityId("food")) == pytest.approx(initial_w2_food + 5.0)


def test_capacity_limits_prevent_infinite_shipping(two_world_trade_state):
    state = two_world_trade_state
    state.active_shipments.clear() # Clear any existing shipments
    state.lane_capacity_tracker.reset() # Reset capacity tracker

    lane = state.lanes[LaneId("l1-2")]
    lane.capacity = 10.0 # Set capacity to allow one trade of 10.0 units

    # Initial inventory of food in w1 is 100.0. build_candidate_trades proposes 10.0
    # Process trade - it should generate a shipment, but limit its quantity by lane.capacity
    initial_w1_food = state.worlds[WorldId("w1")].market.inventory.get(CommodityId("food"))
    
    process_trade(state) # This will build candidates and try to add them
    
    # There should be exactly one shipment in active_shipments
    assert len(state.active_shipments) == 1
    shipment = state.active_shipments[0]
    
    # The quantity of the shipment should be 5.0 (limited by available inventory)
    assert shipment.quantity == pytest.approx(5.0)
    
    # The source world should have reduced its inventory by the shipped amount
    assert state.worlds[WorldId("w1")].market.inventory.get(CommodityId("food")) == pytest.approx(initial_w1_food - 5.0)
    
    # Let's ensure the lane capacity tracker is updated
    assert state.lane_capacity_tracker.used_capacity[lane.id] == pytest.approx(5.0)


def test_trade_convergence_reduces_price_gradient_integration(two_world_trade_state):
    state = two_world_trade_state
    
    w1 = state.worlds[WorldId("w1")]
    w2 = state.worlds[WorldId("w2")]
    
    initial_food_price_w1 = w1.market.prices[CommodityId("food")] # 8.0
    initial_food_price_w2 = w2.market.prices[CommodityId("food")] # 15.0
    
    # Run several ticks to allow trade to occur and prices to adjust
    for _ in range(10):
        step(state)
        # In each step, trade will occur, food will move from w1 to w2.
        # w1 food inventory decreases -> price increases
        # w2 food inventory increases -> price decreases
        # This should reduce the price gradient.
    
    final_food_price_w1 = w1.market.prices[CommodityId("food")]
    final_food_price_w2 = w2.market.prices[CommodityId("food")]

    # Check that prices have moved towards convergence
    assert final_food_price_w1 > initial_food_price_w1 # W1 price should increase
    assert final_food_price_w2 < initial_food_price_w2 # W2 price should decrease
    
    # Check that the price difference has reduced
    initial_price_diff = abs(initial_food_price_w2 - initial_food_price_w1)
    final_price_diff = abs(final_food_price_w2 - final_food_price_w1)
    assert final_price_diff < initial_price_diff
