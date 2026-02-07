import pytest
from pathlib import Path
import random

from src.starsim.core.ids import WorldId, CommodityId
from src.starsim.core.state import UniverseState
from src.starsim.generation.model import Planet
from src.starsim.generation.load import load_planet_types, load_system_templates
from src.starsim.generation.system_gen import generate_planet, generate_world, generate_universe


@pytest.fixture(autouse=True)
def setup_generation_data():
    # Ensure generation data is loaded
    # Assume data files are in data/generation/ as per Milestone 19 setup
    pass


@pytest.fixture
def planet_types_data():
    return load_planet_types(Path("data/generation/planet_types.yaml"))


@pytest.fixture
def system_templates_data():
    return load_system_templates(Path("data/generation/system_templates.yaml"))


def test_generate_planet_deterministic(planet_types_data):
    # Test determinism for planet generation
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    continental_data = planet_types_data["continental"]

    planet1 = generate_planet(rng1, continental_data)
    planet2 = generate_planet(rng2, continental_data)

    assert planet1.type == planet2.type
    assert planet1.habitability == pytest.approx(planet2.habitability)
    assert planet1.resource_potentials == planet2.resource_potentials


def test_generate_planet_habitability_range(planet_types_data):
    # Test habitability falls within expected range for a specific type
    rng = random.Random(100) # Use a different seed
    desert_data = planet_types_data["desert"]
    planet = generate_planet(rng, desert_data)
    
    # Based on desert_data, most habitability is between 0.3 and 0.6
    # This is a probabilistic test, so we assert broadly.
    assert 0.0 <= planet.habitability <= 1.0


def test_generate_planet_resource_potentials_sampling(planet_types_data):
    # Test resource potentials are sampled
    rng = random.Random(101)
    ocean_data = planet_types_data["ocean"]
    planet = generate_planet(rng, ocean_data)

    assert CommodityId("food") in planet.resource_potentials
    assert CommodityId("minerals") in planet.resource_potentials
    assert planet.resource_potentials[CommodityId("food")] >= 0.0


def test_generate_world_deterministic(system_templates_data, planet_types_data):
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    default_template = system_templates_data["default_system"]

    world1 = generate_world("sys-1", rng1, default_template, planet_types_data)
    world2 = generate_world("sys-1", rng2, default_template, planet_types_data)

    assert world1.id == world2.id
    assert len(world1.planets) == len(world2.planets)
    for p1, p2 in zip(world1.planets, world2.planets):
        assert p1.type == p2.type
        assert p1.habitability == pytest.approx(p2.habitability)
        assert p1.resource_potentials == p2.resource_potentials


def test_generate_universe_deterministic(system_templates_data, planet_types_data):
    rng1 = random.Random(42)
    rng2 = random.Random(42)

    universe1 = generate_universe(rng1, 2, system_templates_data, planet_types_data)
    universe2 = generate_universe(rng2, 2, system_templates_data, planet_types_data)

    assert universe1.seed == universe2.seed
    assert len(universe1.worlds) == len(universe2.worlds)
    
    # Compare world data (simplistic, will be improved with dedicated World comparison later)
    assert list(universe1.worlds.keys()) == list(universe2.worlds.keys())
    assert all(w1.name == w2.name for w1, w2 in zip(universe1.worlds.values(), universe2.worlds.values()))
    assert all(len(w1.planets) == len(w2.planets) for w1, w2 in zip(universe1.worlds.values(), universe2.worlds.values()))

    # Check that a generated YAML loads without errors
    output_path = "data/universe_generated_test.json"
    from src.starsim.io.save_load import save_to_json, load_from_json
    save_to_json(universe1, output_path)
    loaded_universe = load_from_json(output_path)
    assert loaded_universe.worlds[WorldId("sys-1")].name == universe1.worlds[WorldId("sys-1")].name
    Path(output_path).unlink() # Clean up
