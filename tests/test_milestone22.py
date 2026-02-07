import pytest
from math import floor # Import floor for population size comparison
from src.starsim.core.ids import WorldId, CommodityId, RecipeId # Import RecipeId
from src.starsim.world.model import World
from src.starsim.generation.model import Planet
from src.starsim.generation.bootstrap import apply_planet_potentials_to_world, BASE_POPULATION, PRODUCTION_CAP_SCALING_FACTOR


def test_apply_planet_potentials_initializes_world_attributes():
    # Create a dummy planet with some potentials
    dummy_planet = Planet(
        type="test_type",
        habitability=0.7,
        resource_potentials={
            CommodityId("food"): 3.0,
            CommodityId("minerals"): 2.0,
            CommodityId("energy"): 1.0,
        },
        tags=set()
    )

    # Create a dummy world with this planet
    dummy_world = World(id=WorldId("test-world"), name="Test World", planets=[dummy_planet])

    # Ensure population and industry are initially None (or as per World's default)
    assert dummy_world.population is None
    assert dummy_world.industry is None

    # Apply potentials
    apply_planet_potentials_to_world(dummy_world)

    # Assert that population and industry are now initialized
    assert dummy_world.population is not None
    assert dummy_world.industry is not None

    # Assert population size
    expected_population_size = max(1, floor(BASE_POPULATION * dummy_planet.habitability))
    assert dummy_world.population.size == expected_population_size

    # Assert stability and prosperity
    assert dummy_world.stability == pytest.approx(dummy_planet.habitability)
    assert dummy_world.prosperity == pytest.approx(dummy_planet.habitability)

    # Assert industry caps
    assert RecipeId("mine_minerals") in dummy_world.industry.caps
    assert dummy_world.industry.caps[RecipeId("mine_minerals")] == pytest.approx(
        dummy_planet.resource_potentials[CommodityId("minerals")] * PRODUCTION_CAP_SCALING_FACTOR +
        dummy_planet.resource_potentials[CommodityId("energy")] * PRODUCTION_CAP_SCALING_FACTOR * 0.5
    )

    assert RecipeId("farm_food") in dummy_world.industry.caps
    assert dummy_world.industry.caps[RecipeId("farm_food")] == pytest.approx(
        dummy_planet.resource_potentials[CommodityId("food")] * PRODUCTION_CAP_SCALING_FACTOR +
        dummy_planet.resource_potentials[CommodityId("energy")] * PRODUCTION_CAP_SCALING_FACTOR * 0.5
    )

    # Check that no other unexpected caps are present (for now, until more recipes are mapped)
    assert len(dummy_world.industry.caps) == 2