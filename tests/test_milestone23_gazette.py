import pytest
from src.starsim.core.state import UniverseState
from src.starsim.core.ids import WorldId # Import WorldId
from src.starsim.world.model import World # Import World
from src.starsim.economy.consumption import Population # Import Population
from src.starsim.reports.gazette import generate_gazette_report


def test_generate_gazette_report_with_shortages_and_booms():
    # Create a dummy UniverseState
    dummy_universe = UniverseState(seed=123, tick=10)

    # Create dummy worlds with different balances
    world1 = World(id=WorldId("w-1"), name="Alpha", stability=0.8, prosperity=0.7)
    world1.population = Population(size=1_000_000)
    world1.food_balance = -500.0 # Shortage
    world1.consumer_goods_balance = 200.0 # Boom
    dummy_universe.worlds[world1.id] = world1

    world2 = World(id=WorldId("w-2"), name="Beta", stability=0.9, prosperity=0.8)
    world2.population = Population(size=2_000_000)
    world2.food_balance = -1000.0 # Shortage
    world2.consumer_goods_balance = -100.0 # Shortage
    dummy_universe.worlds[world2.id] = world2

    world3 = World(id=WorldId("w-3"), name="Gamma", stability=0.7, prosperity=0.6)
    world3.population = Population(size=500_000)
    world3.food_balance = -100.0 # Minor shortage
    world3.consumer_goods_balance = -50.0 # Minor shortage
    dummy_universe.worlds[world3.id] = world3
    
    world4 = World(id=WorldId("w-4"), name="Delta", stability=0.7, prosperity=0.6)
    world4.population = Population(size=500_000)
    world4.food_balance = 50.0 # Minor boom
    world4.consumer_goods_balance = 500.0 # Major boom
    dummy_universe.worlds[world4.id] = world4


    report = generate_gazette_report(dummy_universe)

    # Assert basic report elements
    assert "--- Galactic Gazette ---" in report
    assert "Date: 10" in report
    assert "--- End Gazette ---" in report

    # Assert Top 3 Shortages
    assert "\n--- Top 3 Shortages ---\n" in report
    assert "1. Food: -1550.00 units deficit" in report
    assert "No significant shortages reported." not in report # Ensure this message is not there

    # Assert Top 3 Booms
    assert "\n--- Top 3 Booms ---\n" in report
    assert "1. Consumer_goods: 550.00 units surplus" in report
    assert "No significant booms reported." not in report # Ensure this message is not there
    assert "2. Food:" not in report # Food is a global shortage, not a boom


    # Assert "No significant shortages/booms reported." is not present if there are shortages/booms
    assert "No significant shortages reported." not in report
    assert "No significant booms reported." not in report

    # Assert Major Faction Shifts placeholder
    assert "\n--- Major Faction Shifts ---\n" in report
    assert "Feature not yet implemented. Requires more complex simulation and historical tracking.\n" in report