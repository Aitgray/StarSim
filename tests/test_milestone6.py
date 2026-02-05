import pytest
from pathlib import Path
from copy import deepcopy

from src.starsim.core.ids import WorldId, CommodityId, RecipeId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.inventory import Inventory
from src.starsim.economy.market import Market
from src.starsim.economy.consumption import Population
from src.starsim.economy.recipes import recipe_registry, Recipe
from src.starsim.economy.production import Industry, produce
from src.starsim.world.load import load_universe
from src.starsim.world.model import World
from src.starsim.core.sim import step


@pytest.fixture
def world_with_industry() -> World:
    world = World(id=WorldId("test_industry_world"), name="Test Industry World")
    
    market = Market()
    market.inventory.add(CommodityId("food"), 0.0) # No initial food
    market.inventory.add(CommodityId("ore"), 100.0) # Some ore for tools
    world.market = market

    industry = Industry(caps={
        RecipeId("farm_food"): 100.0, # Produces 100 food
        RecipeId("assemble_tools"): 10.0 # Produces 10 tools, needs 100 ore
    })
    world.industry = industry
    
    return world


@pytest.fixture
def universe_state_for_production(world_with_industry) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_industry.id] = world_with_industry
    return state


def test_production_limited_by_capacity(universe_state_for_production):
    world = universe_state_for_production.worlds[WorldId("test_industry_world")]
    market = world.market
    industry = world.industry
    
    initial_food = market.inventory.get(CommodityId("food"))
    
    produce(world, universe_state_for_production)
    
    # farm_food produces 100 food per production unit, and cap is 10 production units, so it should produce 1000 food
    assert market.inventory.get(CommodityId("food")) == pytest.approx(initial_food + 1000.0)


def test_production_limited_by_input_availability(universe_state_for_production):
    world = universe_state_for_production.worlds[WorldId("test_industry_world")]
    market = world.market
    industry = world.industry

    # Set ore to only allow production of 5 tools (needs 10 ore per tool, so 50 ore total)
    market.inventory[CommodityId("ore")] = 50.0 
    
    initial_ore = market.inventory.get(CommodityId("ore"))
    initial_tools = market.inventory.get(CommodityId("tools"))
    
    produce(world, universe_state_for_production)
    
    # assemble_tools cap is 10.0, but only 50 ore means max 5 tools can be produced
    assert market.inventory.get(CommodityId("ore")) == pytest.approx(initial_ore - 50.0)
    assert market.inventory.get(CommodityId("tools")) == pytest.approx(initial_tools + 5.0)


def test_no_negative_inventory_after_production(universe_state_for_production):
    world = universe_state_for_production.worlds[WorldId("test_industry_world")]
    market = world.market

    # Set ore to a very low amount, e.g., 5.0, so it's less than required for even one tool
    market.inventory[CommodityId("ore")] = 5.0
    
    produce(world, universe_state_for_production)
    
    assert market.inventory.get(CommodityId("ore")) >= 0.0
    assert market.inventory.get(CommodityId("tools")) >= 0.0


def test_agri_world_produces_food_and_stabilizes_self_integration():
    # Create a simple agri world
    state = UniverseState(seed=42)
    agri_world_id = WorldId("agri")
    agri_world = World(id=agri_world_id, name="Agri World")
    
    market = Market()
    market.inventory.add(CommodityId("food"), 0.0) # Initially no food
    market.prices[CommodityId("food")] = commodity_registry.get(CommodityId("food")).base_price
    agri_world.market = market

    population = Population(size=1_000, needs={CommodityId("food"): 0.1}) # Needs 100 food per tick
    agri_world.population = population

    industry = Industry(caps={RecipeId("farm_food"): 1.5}) # Produces 150 food per tick (1.5 * 100)
    agri_world.industry = industry
    
    agri_world.stability = 0.5
    agri_world.unrest = 0.5
    agri_world.scarcity = 0.5
    
    state.worlds[agri_world_id] = agri_world

    # Run for several ticks
    # Capture initial values BEFORE any steps
    original_stability = agri_world.stability
    original_unrest = agri_world.unrest
    original_scarcity = agri_world.scarcity
    
    # Simulate enough ticks for production to overcome shortage and stabilize
    for _ in range(5): 
        step(state)

    # After some ticks, food inventory should increase, and instability should have initially worsened then stabilized
    assert agri_world.market.inventory.get(CommodityId("food")) > 50.0 # Should have produced more food
    assert agri_world.stability < original_stability # Stability should have decreased
    assert agri_world.unrest > original_unrest       # Unrest should have increased
    assert agri_world.scarcity > original_scarcity   # Scarcity should have increased

    # Check bounds
    assert 0.0 <= agri_world.stability <= 1.0
    assert 0.0 <= agri_world.unrest <= 1.0
    assert 0.0 <= agri_world.scarcity <= 1.0
