import pytest
from pathlib import Path

from src.starsim.generation.load import load_planet_types, load_system_templates, GenerationSchemaError


@pytest.fixture
def planet_types_path() -> Path:
    return Path("data/generation/planet_types.yaml")


@pytest.fixture
def system_templates_path() -> Path:
    return Path("data/generation/system_templates.yaml")


def test_load_planet_types_success(planet_types_path):
    planet_types = load_planet_types(planet_types_path)
    assert "continental" in planet_types
    assert "desert" in planet_types
    assert "ocean" in planet_types
    assert planet_types["continental"]["weight"] == 12


def test_load_system_templates_success(system_templates_path):
    system_templates = load_system_templates(system_templates_path)
    assert "default_system" in system_templates
    assert system_templates["default_system"]["min_planets"] == 2


def test_planet_types_invalid_schema_missing_id(tmp_path):
    invalid_yaml = """
planet_types:
  - name: "Invalid"
    weight: 10
    habitability_distribution: []
    resource_tables: {}
"""
    path = tmp_path / "invalid_planet_types.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="Missing key 'id'"):
        load_planet_types(path)


def test_planet_types_invalid_schema_invalid_weight(tmp_path):
    invalid_yaml = """
planet_types:
  - id: "invalid_weight"
    name: "Invalid Weight"
    weight: -1
    habitability_distribution: []
    resource_tables: {}
"""
    path = tmp_path / "invalid_planet_types.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="Invalid 'weight'"):
        load_planet_types(path)


def test_system_templates_invalid_schema_missing_min_planets(tmp_path):
    invalid_yaml = """
system_templates:
  - id: "invalid_system"
    name: "Invalid System"
    max_planets: 5
    planet_type_weights: {}
"""
    path = tmp_path / "invalid_system_templates.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="Missing key 'min_planets'"):
        load_system_templates(path)


def test_system_templates_invalid_schema_max_less_than_min(tmp_path):
    invalid_yaml = """
system_templates:
  - id: "invalid_system"
    name: "Invalid System"
    min_planets: 5
    max_planets: 2
    planet_type_weights: {}
"""
    path = tmp_path / "invalid_system_templates.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="Invalid 'max_planets'"):
        load_system_templates(path)


def test_resource_potential_invalid_definition(tmp_path):
    invalid_yaml = """
planet_types:
  - id: "test"
    name: "Test"
    weight: 1
    habitability_distribution:
      - band: [0.5, 0.8]
        weight: 1
    resource_tables:
      habitable:
        when_habitability_gte: 0.5
        potentials:
          energy: {invalid_key: [1, 2]}
"""
    path = tmp_path / "invalid_resource.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="must define 'range' or 'bins'"):
        load_planet_types(path)


def test_resource_potential_invalid_range_data(tmp_path):
    invalid_yaml = """
planet_types:
  - id: "test"
    name: "Test"
    weight: 1
    habitability_distribution:
      - band: [0.5, 0.8]
        weight: 1
    resource_tables:
      habitable:
        when_habitability_gte: 0.5
        potentials:
          minerals: {range: [5, 1]} # min > max
"""
    path = tmp_path / "invalid_resource.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="Invalid range"):
        load_planet_types(path)


def test_resource_potential_invalid_bins_data(tmp_path):
    invalid_yaml = """
planet_types:
  - id: "test"
    name: "Test"
    weight: 1
    habitability_distribution:
      - band: [0.5, 0.8]
        weight: 1
    resource_tables:
      habitable:
        when_habitability_gte: 0.5
        potentials:
          food:
            bins:
              - value: 1
                weight: -1 # negative weight
"""
    path = tmp_path / "invalid_resource.yaml"
    path.write_text(invalid_yaml)
    with pytest.raises(GenerationSchemaError, match="Invalid bins"):
        load_planet_types(path)
