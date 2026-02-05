import pytest
from pathlib import Path # Add this import for Path

from src.starsim.core.state import UniverseState
from src.starsim.core.sim import step, TickReport
from src.starsim.reports.gazette import generate_gazette
from src.starsim.world.load import load_universe # Add this import


@pytest.fixture
def initial_state() -> UniverseState:
    return UniverseState(seed=42)


def test_step_increments_tick(initial_state):
    initial_tick = initial_state.tick
    report = step(initial_state)
    assert initial_state.tick == initial_tick + 1
    assert report.tick == initial_state.tick


def test_log_entries_appear(initial_state):
    # Load universe with market data to ensure market price updates are logged
    state_with_market = load_universe(Path("data/universe.yaml"))
    
    report = step(state_with_market)
    
    # Collect all log entry types
    log_types = {entry.type for entry in report.log.entries}
    
    # Assert presence of expected log types for a populated/industrial world (sol)
    assert "economy.production.output" in log_types
    assert "economy.consumption.impact" in log_types
    assert "economy.prices.update" in log_types

    # Assert presence of expected log types for unpopulated/non-industrial worlds (alpha-centauri, proxima-centauri)
    assert "economy.production" in log_types # "No industry or market" message
    assert "economy.consumption" in log_types # "No population or market" message
    assert "economy.prices" in log_types # "No market in world" message
    
    # Assert presence of generic placeholder stages (either 'events.roll' or 'event.triggered')
    assert "economy.trade" in log_types
    assert "factions.step" in log_types
    assert ("events.roll" in log_types or "event.triggered" in log_types)

    # Assert a reasonable total number of logs
    assert len(report.log.entries) >= 9 # At least one for each expected type



def test_determinism_of_tick_report():
    # State 1
    state1 = UniverseState(seed=123)
    report1 = step(state1)

    # State 2 - with same seed
    state2 = UniverseState(seed=123)
    report2 = step(state2)

    # Compare the logs
    assert len(report1.log.entries) == len(report2.log.entries)
    for entry1, entry2 in zip(report1.log.entries, report2.log.entries):
        # We can't compare the objects directly, so we compare their dict representations
        assert entry1.__dict__ == entry2.__dict__


def test_gazette_generation(initial_state):
    initial_tick = initial_state.tick
    report = step(initial_state)
    gazette = generate_gazette(report.log, tick=initial_tick)

    # Check for some expected content
    assert f"== Tick {initial_tick} Report ==" in gazette
    assert "[economy.trade] No active trade or arrivals." in gazette
    assert "[factions.step] Faction actions applied." in gazette
    assert "[events.roll] No events triggered this tick." in gazette # Expect no events triggered message
    assert "economy.production" not in gazette # Should not have production logs
    assert "economy.consumption" not in gazette # Should not have consumption logs
    assert "economy.prices" not in gazette # Should not have prices logs
