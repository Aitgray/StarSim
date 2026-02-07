import pytest
from pathlib import Path

from src.starsim.core.ids import WorldId, CommodityId, RecipeId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.market import Market
from src.starsim.economy.production import Industry, produce
from src.starsim.world.model import World


# Fixtures for specific refinery types
@pytest.fixture
def world_with_alloy_refinery() -> World:
    world = World(id=WorldId("test_alloy_refinery_world"), name="Test Alloy Refinery World")
    
    market = Market()
    market.inventory.add(CommodityId("minerals"), 100.0)
    market.inventory.add(CommodityId("energy"), 100.0)
    market.inventory.add(CommodityId("alloy"), 0.0)
    world.market = market

    industry = Industry(caps={
        RecipeId("refine_alloy"): 10.0, # Produces 10 alloy units per production unit (needs 50 minerals, 20 energy)
    })
    world.industry = industry
    
    return world


@pytest.fixture
def world_with_cg_refinery() -> World:
    world = World(id=WorldId("test_cg_refinery_world"), name="Test CG Refinery World")
    
    market = Market()
    market.inventory.add(CommodityId("minerals"), 100.0)
    market.inventory.add(CommodityId("energy"), 100.0)
    market.inventory.add(CommodityId("consumer_goods"), 0.0)
    world.market = market

    industry = Industry(caps={
        RecipeId("refine_consumer_goods"): 10.0 # Produces 10 consumer goods units per production unit (needs 30 minerals, 10 energy)
    })
    world.industry = industry
    
    return world


@pytest.fixture
def universe_state_for_alloy_refinery(world_with_alloy_refinery) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_alloy_refinery.id] = world_with_alloy_refinery
    return state


@pytest.fixture
def universe_state_for_cg_refinery(world_with_cg_refinery) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_cg_refinery.id] = world_with_cg_refinery
    return state


def test_refine_alloy_produces_alloy_consumes_minerals_energy(universe_state_for_alloy_refinery):
    world = universe_state_for_alloy_refinery.worlds[WorldId("test_alloy_refinery_world")]
    
    initial_minerals = world.market.inventory.get(CommodityId("minerals"))
    initial_energy = world.market.inventory.get(CommodityId("energy"))
    initial_alloy = world.market.inventory.get(CommodityId("alloy"))

    produce(world, universe_state_for_alloy_refinery)

    # 10 production units of refine_alloy will consume 50 minerals and 20 energy, produce 10 alloy
    assert world.market.inventory.get(CommodityId("minerals")) == pytest.approx(initial_minerals - 50.0)
    assert world.market.inventory.get(CommodityId("energy")) == pytest.approx(initial_energy - 20.0)
    assert world.market.inventory.get(CommodityId("alloy")) == pytest.approx(initial_alloy + 10.0)


def test_refine_consumer_goods_produces_cg_consumes_minerals_energy(universe_state_for_cg_refinery):
    world = universe_state_for_cg_refinery.worlds[WorldId("test_cg_refinery_world")]
    
    initial_minerals = world.market.inventory.get(CommodityId("minerals"))
    initial_energy = world.market.inventory.get(CommodityId("energy"))
    initial_consumer_goods = world.market.inventory.get(CommodityId("consumer_goods"))

    produce(world, universe_state_for_cg_refinery)

    # 10 production units of refine_consumer_goods will consume 30 minerals and 10 energy, produce 10 consumer_goods
    assert world.market.inventory.get(CommodityId("minerals")) == pytest.approx(initial_minerals - 30.0)
    assert world.market.inventory.get(CommodityId("energy")) == pytest.approx(initial_energy - 10.0)
    assert world.market.inventory.get(CommodityId("consumer_goods")) == pytest.approx(initial_consumer_goods + 10.0)


def test_production_limited_by_energy_availability(universe_state_for_alloy_refinery):
    world = universe_state_for_alloy_refinery.worlds[WorldId("test_alloy_refinery_world")]
    
    # Set energy to only allow production of 5 alloy (needs 2 energy per alloy, so 10 energy total for 5 alloy)
    world.market.inventory[CommodityId("energy")] = 10.0
    world.market.inventory[CommodityId("minerals")] = 1000.0 # Abundant minerals

    initial_energy = world.market.inventory.get(CommodityId("energy"))
    initial_alloy = world.market.inventory.get(CommodityId("alloy"))
    
    produce(world, universe_state_for_alloy_refinery)

    # refine_alloy cap is 10.0, but only 10 energy means max 5 alloys can be produced
    assert world.market.inventory.get(CommodityId("energy")) == pytest.approx(initial_energy - 10.0)
    assert world.market.inventory.get(CommodityId("alloy")) == pytest.approx(initial_alloy + 5.0)