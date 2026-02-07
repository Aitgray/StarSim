import pytest
from pathlib import Path

from src.starsim.core.ids import CommodityId
from src.starsim.generation.model import Planet


def test_planet_creation():
    planet = Planet(
        type="continental",
        habitability=0.85,
        resource_potentials={
            CommodityId("minerals"): 3.0,
            CommodityId("food"): 5.0
        },
        tags={"temperate", "lush"}
    )

    assert planet.type == "continental"
    assert planet.habitability == pytest.approx(0.85)
    assert planet.resource_potentials[CommodityId("minerals")] == pytest.approx(3.0)
    assert planet.resource_potentials[CommodityId("food")] == pytest.approx(5.0)
    assert "temperate" in planet.tags
    assert "lush" in planet.tags
    assert len(planet.tags) == 2


def test_planet_default_values():
    planet = Planet(type="desert", habitability=0.2)
    assert planet.resource_potentials == {}
    assert planet.tags == set()


def test_planet_resource_potentials_commodity_id():
    planet = Planet(
        type="ocean",
        habitability=0.6,
        resource_potentials={
            "energy": 2.5, # Test string input for CommodityId
            CommodityId("alloy"): 0.5
        }
    )
    assert isinstance(list(planet.resource_potentials.keys())[0], str)
    assert planet.resource_potentials[CommodityId("energy")] == pytest.approx(2.5)
