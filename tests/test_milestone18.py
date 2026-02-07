import pytest
from pathlib import Path

from src.starsim.core.ids import WorldId, CommodityId, RecipeId
from src.starsim.core.state import UniverseState
from src.starsim.economy.commodities import commodity_registry
from src.starsim.economy.market import Market
from src.starsim.economy.production import Industry
from src.starsim.economy.consumption import Population
from src.starsim.economy.upkeep import apply_upkeep
from src.starsim.world.model import World


@pytest.fixture(autouse=True)
def setup_commodities():
    if not commodity_registry._commodities:
        commodity_registry.load_from_yaml(Path("data/commodities.yaml"))


@pytest.fixture
def world_with_energy_upkeep() -> World:
    world = World(id=WorldId("test_upkeep_world"), name="Test Upkeep World")
    
    market = Market()
    market.inventory.add(CommodityId("energy"), 100.0) # Some initial energy
    world.market = market

    population = Population(
        size=1000,
        energy_upkeep_per_capita_per_tick=0.01 # Needs 10 energy (1000 * 0.01)
    )
    world.population = population

    industry = Industry(caps={
        RecipeId("mine_minerals"): 10.0, # Total cap 10.0
        RecipeId("farm_food"): 5.0 # Total cap 5.0
    })
    world.industry = industry
    
    world.stability = 0.8
    world.prosperity = 0.8
    
    return world


@pytest.fixture
def universe_state_for_upkeep(world_with_energy_upkeep) -> UniverseState:
    state = UniverseState(seed=123)
    state.worlds[world_with_energy_upkeep.id] = world_with_energy_upkeep
    return state


def test_energy_upkeep_consumes_energy(universe_state_for_upkeep):
    world = universe_state_for_upkeep.worlds[WorldId("test_upkeep_world")]
    initial_energy = world.market.inventory.get(CommodityId("energy"))
    
    # Expected upkeep: pop (1000*0.01=10) + infrastructure (15*0.1=1.5) = 11.5
    expected_consumed_energy = 11.5
    
    apply_upkeep(world, universe_state_for_upkeep)
    
    assert world.market.inventory.get(CommodityId("energy")) == pytest.approx(initial_energy - expected_consumed_energy)


def test_energy_deficit_reduces_stability_prosperity_throttles_caps(universe_state_for_upkeep):
    world = universe_state_for_upkeep.worlds[WorldId("test_upkeep_world")]
    
    # Set energy to a very low amount to ensure deficit
    world.market.inventory[CommodityId("energy")] = 5.0 # Needed 11.5, available 5.0 -> deficit
    
    initial_stability = world.stability
    initial_prosperity = world.prosperity
    initial_mine_minerals_cap = world.industry.caps.get(RecipeId("mine_minerals"))
    
    apply_upkeep(world, universe_state_for_upkeep)
    
    # Stability and prosperity should decrease
    assert world.stability < initial_stability
    assert world.prosperity < initial_prosperity
    
    # Production caps should be throttled
    assert world.industry.caps.get(RecipeId("mine_minerals")) < initial_mine_minerals_cap

    # Check bounds
    assert 0.0 <= world.stability <= 1.0
    assert 0.0 <= world.prosperity <= 1.0
    assert world.industry.caps.get(RecipeId("mine_minerals")) >= 0.0


def test_no_energy_deficit_no_penalties(universe_state_for_upkeep):
    world = universe_state_for_upkeep.worlds[WorldId("test_upkeep_world")]
    
    # Provide abundant energy
    world.market.inventory.add(CommodityId("energy"), 1000.0) # More than needed
    
    initial_stability = world.stability
    initial_prosperity = world.prosperity
    initial_mine_minerals_cap = world.industry.caps.get(RecipeId("mine_minerals"))
    
    apply_upkeep(world, universe_state_for_upkeep)
    
    # Stability and prosperity should remain unchanged
    assert world.stability == initial_stability
    assert world.prosperity == initial_prosperity
    
    # Production caps should remain unchanged
    assert world.industry.caps.get(RecipeId("mine_minerals")) == initial_mine_minerals_cap
