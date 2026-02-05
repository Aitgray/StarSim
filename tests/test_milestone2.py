import pytest
import os
from pathlib import Path

from src.starsim.world.load import load_universe, UniverseSchemaError
from src.starsim.io.save_load import save_to_json, load_from_json, to_dict, from_dict


@pytest.fixture
def universe_yaml_path() -> Path:
    return Path("data/universe.yaml")


def test_yaml_load_produces_correct_counts(universe_yaml_path):
    state = load_universe(universe_yaml_path)
    assert len(state.worlds) == 3
    assert len(state.lanes) == 3


def test_yaml_load_invalid_lane_reference_raises_error():
    invalid_yaml = """
seed: 1
worlds:
  - id: "w1"
    name: "World 1"
lanes:
  - id: "l1"
    a: "w1"
    b: "w2" # w2 does not exist
"""
    # Use a temporary file
    with open("invalid_universe.yaml", "w") as f:
        f.write(invalid_yaml)
    
    with pytest.raises(UniverseSchemaError):
        load_universe(Path("invalid_universe.yaml"))

    os.remove("invalid_universe.yaml")


def test_load_save_load_round_trip(universe_yaml_path):
    # Load initial state from YAML
    initial_state = load_universe(universe_yaml_path)

    # Save to a temporary JSON file
    save_path = "test_round_trip.json"
    save_to_json(initial_state, save_path)

    # Load back from JSON
    loaded_state = load_from_json(save_path)

    # Clean up the temporary file
    os.remove(save_path)

    # Assert that the loaded state is equivalent
    assert initial_state.seed == loaded_state.seed
    assert initial_state.tick == loaded_state.tick
    assert len(initial_state.worlds) == len(loaded_state.worlds)
    assert len(initial_state.lanes) == len(loaded_state.lanes)

    # Compare dict representations (ignoring derived adjacency)
    initial_dict = to_dict(initial_state)
    loaded_dict = to_dict(loaded_state)

    # Sort lists to ensure order doesn't matter
    initial_dict['worlds'].sort(key=lambda x: x['id'])
    loaded_dict['worlds'].sort(key=lambda x: x['id'])
    initial_dict['lanes'].sort(key=lambda x: x['id'])
    loaded_dict['lanes'].sort(key=lambda x: x['id'])

    assert initial_dict == loaded_dict
