from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Dict, List, Any
import yaml

from ..core.ids import CommodityId, RecipeId

logger = logging.getLogger(__name__)

@dataclass
class Recipe:
    id: RecipeId
    name: str
    inputs: Dict[CommodityId, float] = field(default_factory=dict)
    outputs: Dict[CommodityId, float] = field(default_factory=dict)
    max_production_units_per_tick: float = 0.0


class RecipeRegistry:
    def __init__(self):
        self._recipes: Dict[RecipeId, Recipe] = {}

    def load_from_yaml(self, path: Path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"YAML file '{path}' is empty or malformed.")
        
        for r_data in data:
            recipe = Recipe(
                id=RecipeId(r_data['id']),
                name=r_data['name'],
                inputs={CommodityId(c_id): qty for c_id, qty in r_data.get('inputs', {}).items()},
                outputs={CommodityId(c_id): qty for c_id, qty in r_data.get('outputs', {}).items()},
                max_production_units_per_tick=r_data.get('max_production_units_per_tick', 0.0)
            )
            self._recipes[recipe.id] = recipe

    def get(self, recipe_id: RecipeId) -> Recipe:
        if recipe_id not in self._recipes:
            raise ValueError(f"Recipe with ID '{recipe_id}' not found.")
        return self._recipes[recipe_id]

    def all_recipes(self) -> List[Recipe]:
        return list(self._recipes.values())

# Global registry instance
recipe_registry = RecipeRegistry()
