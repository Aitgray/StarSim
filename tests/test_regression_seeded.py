import pytest
from pathlib import Path
import json
from typing import Dict, Any # Added for Dict and Any

from src.starsim.core.state import UniverseState
from src.starsim.core.sim import step
from src.starsim.world.load import load_universe
from src.starsim.economy.trade import process_trade
from src.starsim.factions.integrate import apply_faction_actions


# Define a fixed scenario for regression testing
REGRESSION_SCENARIO_PATH = Path("data/universe.yaml")
REGRESSION_TICKS = 5


def get_summary_metrics(state: UniverseState) -> Dict[str, Any]:
    """Extracts key metrics from the UniverseState for regression comparison."""
    summary = {
        "seed": state.seed,
        "tick": state.tick,
        "world_prices": {},
        "world_controls": {},
        "total_trade_volume": 0.0, # Will be calculated during trade processing
        "lane_hazards": {},
    }

    # World Prices
    for world_id, world in state.worlds.items():
        if world.market:
            # Sort prices to ensure consistent comparison
            sorted_prices = sorted(
                [(c_id, price) for c_id, price in world.market.prices.items()],
                key=lambda item: item[1],
                reverse=True
            )
            summary["world_prices"][world_id] = {c_id: price for c_id, price in sorted_prices[:3]} # Top 3

    # World Controls
    for world_id, world in state.worlds.items():
        if world.control:
            summary["world_controls"][world_id] = world.control

    # Lane Hazards
    for lane_id, lane in state.lanes.items():
        summary["lane_hazards"][lane_id] = lane.hazard
    
    # Total Trade Volume (this requires inspecting logs or aggregating shipments)
    # For now, let's just make sure active_shipments list is stable
    summary["active_shipments_count"] = len(state.active_shipments)
    # This metric is hard to stabilize without full trade processing, so maybe skip for now.

    return summary


def test_seeded_regression():
    """
    Loads a fixed scenario, runs it for N ticks, and compares the summary metrics
    against a golden file.
    """
    initial_state = load_universe(REGRESSION_SCENARIO_PATH)
    
    # Run simulation for fixed number of ticks
    for _ in range(REGRESSION_TICKS):
        step(initial_state)

    current_summary = get_summary_metrics(initial_state)

    # Define path to the golden file (create it if it doesn't exist for first run)
    golden_file_path = Path(__file__).parent / "regression_golden.json"

    if not golden_file_path.exists():
        print(f"Regression golden file not found. Creating: {golden_file_path}")
        with open(golden_file_path, "w") as f:
            json.dump(current_summary, f, indent=2)
        pytest.fail("Regression golden file created. Run test again.")

    with open(golden_file_path, "r") as f:
        golden_summary = json.load(f)

    # Compare current metrics against golden metrics
    assert current_summary == golden_summary
