import pytest
from pathlib import Path

from src.starsim.core.ids import WorldId, CommodityId, RecipeId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.market import Market
from src.starsim.economy.production import Industry
from src.starsim.economy.investment import invest_civilian, invest_military
from src.starsim.world.model import World


@pytest.fixture
def world_with_investment_capacity() -> World:
    world = World(id=WorldId("test_investment_world"), name="Test Investment World")
    
    market = Market()
    market.inventory.add(CommodityId("minerals"), 100.0)
    market.inventory.add(CommodityId("alloy"), 100.0)
    world.market = market

    industry = Industry(caps={
        RecipeId("mine_minerals"): 10.0, # Only one civilian recipe for testing
        RecipeId("assemble_alloys"): 10.0, # Only one military recipe for testing
    })
    world.industry = industry
    
    return world


@pytest.fixture
def universe_state_for_investment(world_with_investment_capacity) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_investment_capacity.id] = world_with_investment_capacity
    return state


def test_invest_civilian_consumes_minerals_increases_cap(universe_state_for_investment):
    world = universe_state_for_investment.worlds[WorldId("test_investment_world")]
    
    initial_minerals = world.market.inventory.get(CommodityId("minerals"))
    initial_mine_minerals_cap = world.industry.caps.get(RecipeId("mine_minerals"), 0.0)

    invest_civilian(world, universe_state_for_investment)

    assert world.market.inventory.get(CommodityId("minerals")) == pytest.approx(initial_minerals - 10.0) # Consumes 10 minerals
    assert world.industry.caps.get(RecipeId("mine_minerals"), 0.0) > initial_mine_minerals_cap # Cap increases


def test_invest_military_consumes_alloys_increases_cap(universe_state_for_investment):
    world = universe_state_for_investment.worlds[WorldId("test_investment_world")]
    
    initial_alloy = world.market.inventory.get(CommodityId("alloy"))
    initial_assemble_alloys_cap = world.industry.caps.get(RecipeId("assemble_alloys"), 0.0)

    invest_military(world, universe_state_for_investment)

    assert world.market.inventory.get(CommodityId("alloy")) == pytest.approx(initial_alloy - 5.0) # Consumes 5 alloy
    assert world.industry.caps.get(RecipeId("assemble_alloys"), 0.0) > initial_assemble_alloys_cap # Cap increases
