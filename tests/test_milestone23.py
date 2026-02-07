import pytest
from src.starsim.core.ids import WorldId, CommodityId
from src.starsim.world.model import World
from src.starsim.economy.consumption import Population
from src.starsim.economy.market import Market
from src.starsim.economy.inventory import Inventory
from src.starsim.reports.world_cards import generate_world_card_report


def test_generate_world_card_report_basic():
    # Create a dummy world with some basic attributes
    dummy_world = World(
        id=WorldId("test-world-23"), 
        name="Alpha Centauri Prime", 
        stability=0.85, 
        prosperity=0.75,
        tech=0.60 # Added tech level
    )
    dummy_world.population = Population(size=5_000_000, growth_rate=0.01) # Added growth_rate for pop trend
    dummy_world.food_balance = -100.0
    dummy_world.starvation_level = 0.05
    dummy_world.consumer_goods_balance = 50.0
    dummy_world.consumer_goods_shortage_level = 0.0

    # Initialize market and inventory for resource ledger
    inventory = Inventory()
    inventory.add(CommodityId("food"), 1000.0)
    inventory.add(CommodityId("minerals"), 500.0)
    market = Market(inventory=inventory, prices={CommodityId("food"): 10.0, CommodityId("minerals"): 5.0})
    dummy_world.market = market

    report = generate_world_card_report(dummy_world)

    # Assert that key information is present in the report
    assert f"--- World Report: Alpha Centauri Prime ({WorldId('test-world-23')}) ---" in report
    assert "Stability: 0.85" in report
    assert "Prosperity: 0.75" in report
    assert "Tech Level: 0.60" in report # New assertion for tech level
    assert "Population: 5000000" in report
    assert "Pop Trend:  (Growth: 1.00%)" in report # New assertion for pop trend
    assert "Food Balance: -100.00 (Starvation: 5.00%)" in report
    assert "Consumer Goods Balance: 50.00 (Shortage: 0.00%)" in report

    # New assertions for Resource Ledger
    assert "--- Resource Ledger ---" in report
    assert "- Food: 1000.00 units (Price: 10.00 energy/unit)" in report
    assert "- Minerals: 500.00 units (Price: 5.00 energy/unit)" in report

    # Ensure the end marker is present
    assert "--- End Report ---" in report