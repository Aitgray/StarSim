from __future__ import annotations
from typing import TYPE_CHECKING
from ..core.ids import CommodityId # Import CommodityId

if TYPE_CHECKING:
    from ..world.model import World


def generate_world_card_report(world: "World"):
    """
    Generates a summary report for a single world, mimicking a "world card" in Stellaris.
    Includes resource ledger, food balance, pop trend, and stability changes.

    Args:
        world: The World object to generate the report for.

    Returns:
        A string containing the formatted report.
    """
    report = f"--- World Report: {world.name} ({world.id}) ---\n"
    report += f"Stability: {world.stability:.2f}\n"
    report += f"Prosperity: {world.prosperity:.2f}\n"
    report += f"Tech Level: {world.tech:.2f}\n" # Added tech level

    if world.population:
        report += f"Population: {world.population.size}\n"
        # Population trend
        pop_change_indicator = ""
        if world.population.growth_rate > 0:
            pop_change_indicator = f" (Growth: {world.population.growth_rate:.2%})"
        elif world.population.growth_rate < 0: # Though currently it only grows or declines via starvation
            pop_change_indicator = f" (Decline: {world.population.growth_rate:.2%})"
        report += f"Pop Trend: {pop_change_indicator}\n" # Placeholder for future more accurate pop trend

        report += f"Food Balance: {world.food_balance:.2f} (Starvation: {world.starvation_level:.2%})\n"
        report += f"Consumer Goods Balance: {world.consumer_goods_balance:.2f} (Shortage: {world.consumer_goods_shortage_level:.2%})\n"
        # TODO: Add stability changes due to consumer goods, unrest, energy upkeep

    # Resource Ledger (current inventory and prices)
    if world.market and world.market.inventory:
        report += "\n--- Resource Ledger ---\n"
        for commodity_id, quantity in world.market.inventory.to_dict().items():
            price = world.market.prices.get(commodity_id, 0.0)
            report += f"- {commodity_id.capitalize()}: {quantity:.2f} units (Price: {price:.2f} energy/unit)\n"
    
    # TODO: Top 3 shortages and booms (this will likely go into gazette.py)

    report += "--- End Report ---\n"
    return report