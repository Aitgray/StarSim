import pytest
from pathlib import Path
import json
import random

from src.starsim.core.state import UniverseState
from src.starsim.generation.system_gen import generate_universe
from src.starsim.generation.load import load_planet_types, load_system_templates


@pytest.fixture(scope="module")
def generation_data():
    """Fixture to load generation data once for the module."""
    planet_types = load_planet_types(Path("data/generation/planet_types.yaml"))
    system_templates = load_system_templates(Path("data/generation/system_templates.yaml"))
    return planet_types, system_templates


@pytest.fixture(scope="module")
def seeded_universe_state(generation_data):
    """Fixture to generate a deterministic universe for regression testing."""
    planet_types, system_templates = generation_data
    test_seed = 12345
    rng = random.Random(test_seed)
    # Generate a small universe for regression testing
    universe = generate_universe(rng, n_systems=2, system_templates_data=system_templates, planet_types_data=planet_types)
    return universe


def normalize_universe_state(universe: UniverseState) -> dict:
    """
    Normalizes the UniverseState for consistent comparison in regression tests.
    Removes non-deterministic elements and formats for easy diffing.
    """
    normalized_data = {
        "seed": universe.seed,
        "tick": universe.tick,
        "worlds": {},
        "lanes": {},
    }

    # Sort worlds and lanes by ID for consistent output
    sorted_world_ids = sorted(universe.worlds.keys())
    sorted_lane_ids = sorted(universe.lanes.keys())

    for world_id in sorted_world_ids:
        world = universe.worlds[world_id]
        normalized_world = {
            "id": world.id,
            "name": world.name,
            "stability": round(world.stability, 4),
            "prosperity": round(world.prosperity, 4),
            "tech": round(world.tech, 4),
            "planets": [],
            # Don't include population, market, industry, factions as they are dynamic
            # and will be tested separately in test_resource_economy_regression.py
            # For now, just focus on the generated structure.
        }
        for planet in sorted(world.planets, key=lambda p: p.type): # Sort planets by type
            normalized_planet = {
                "type": planet.type,
                "habitability": round(planet.habitability, 4),
                "resource_potentials": {
                    cid: round(potential, 4) for cid, potential in sorted(planet.resource_potentials.items())
                },
                # Tags can be dynamic, so let's sort them for consistent output
                "tags": sorted(list(planet.tags)),
            }
            normalized_world["planets"].append(normalized_planet)
        normalized_data["worlds"][world_id] = normalized_world

    for lane_id in sorted_lane_ids:
        lane = universe.lanes[lane_id]
        normalized_lane = {
            "id": lane.id,
            "a": lane.a,
            "b": lane.b,
            "distance": round(lane.distance, 4),
            "hazard": round(lane.hazard, 4),
            "capacity": round(lane.capacity, 4),
        }
        normalized_data["lanes"][lane_id] = normalized_lane

    return normalized_data


# Define the path to the golden file
GOLDEN_FILE = Path("tests/regression_golden.json")


def test_generator_regression(seeded_universe_state):
    """
    Tests that universe generation remains consistent for a given seed.
    Compares normalized output against a golden JSON file.
    """
    # Generate the current state for comparison
    current_normalized_state = normalize_universe_state(seeded_universe_state)

    # Load the golden state
    if not GOLDEN_FILE.exists():
        pytest.fail(f"Golden file '{GOLDEN_FILE}' not found. Run with '--update-goldens' to create it.")

    with open(GOLDEN_FILE, "r") as f:
        golden_normalized_state = json.load(f)

    # Compare
    assert current_normalized_state == golden_normalized_state, (
        f"Generated universe state does not match golden file '{GOLDEN_FILE}'. "
        "Run with '--update-goldens' to update if changes are intentional."
    )

@pytest.fixture(autouse=True)
def check_golden_file_update(request):
    """
    A fixture to automatically update the golden file if the --update-goldens flag is used.
    """
    yield
    if request.config.option.update_goldens: # Changed here
        planet_types, system_templates = request.getfixturevalue("generation_data")
        test_seed = 12345
        rng = random.Random(test_seed)
        universe = generate_universe(rng, n_systems=2, system_templates_data=system_templates, planet_types_data=planet_types)
        current_normalized_state = normalize_universe_state(universe)
        
        print(f"\nUpdating golden file: {GOLDEN_FILE}")
        with open(GOLDEN_FILE, "w") as f:
            json.dump(current_normalized_state, f, indent=2)
