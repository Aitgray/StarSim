from typing import List, Tuple
from collections import defaultdict

from ..core.ids import CommodityId
from ..core.log import AuditLog


def generate_gazette_report(universe):
    """
    Generates a gazette report for the entire universe, summarizing key events and trends.

    Args:
        universe: The UniverseState object to generate the report for.

    Returns:
        A string containing the formatted report.
    """
    report = "--- Galactic Gazette ---\n"
    report += f"Date: {universe.tick}\n"

    # Aggregate resource balances across all worlds
    global_balances = defaultdict(float)
    for world_id, world in universe.worlds.items():
        if world.population:
            global_balances[CommodityId("food")] += world.food_balance
            global_balances[CommodityId("consumer_goods")] += world.consumer_goods_balance
        # For other resources, we would need a more sophisticated production/consumption tracker per world
        # For now, we only track food and consumer goods balances explicitly from World model.

    # Identify shortages and booms
    shortages: List[Tuple[CommodityId, float]] = []
    booms: List[Tuple[CommodityId, float]] = []

    for commodity_id, balance in global_balances.items():
        if balance < 0:
            shortages.append((commodity_id, balance))
        elif balance > 0:
            booms.append((commodity_id, balance))

    # Sort by severity (most negative balance for shortages, most positive for booms)
    shortages.sort(key=lambda x: x[1]) # Sorts from most negative to least negative
    booms.sort(key=lambda x: x[1], reverse=True) # Sorts from most positive to least positive

    # Top 3 Shortages
    report += "\n--- Top 3 Shortages ---\n"
    if not shortages:
        report += "No significant shortages reported.\n"
    else:
        for i, (commodity_id, balance) in enumerate(shortages[:3]):
            report += f"{i+1}. {commodity_id.capitalize()}: {balance:.2f} units deficit\n"

    # Top 3 Booms
    report += "\n--- Top 3 Booms ---\n"
    if not booms:
        report += "No significant booms reported.\n"
    else:
        for i, (commodity_id, balance) in enumerate(booms[:3]):
            report += f"{i+1}. {commodity_id.capitalize()}: {balance:.2f} units surplus\n"

    # Major Faction Shifts
    report += "\n--- Major Faction Shifts ---\n"
    report += "Feature not yet implemented. Requires more complex simulation and historical tracking.\n"

    report += "\n--- End Gazette ---\n"
    return report


def generate_gazette(log: AuditLog, tick: int) -> str:
    """
    Generates a concise gazette report from an AuditLog.
    """
    lines = [f"== Tick {tick} Report =="]
    for entry in log.entries:
        reason = entry.reason or ""
        if reason:
            lines.append(f"[{entry.type}] {reason}")
        else:
            lines.append(f"[{entry.type}]")
    return "\n".join(lines) + "\n"
