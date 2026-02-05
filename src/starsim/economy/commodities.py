from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any
import yaml

from ..core.ids import CommodityId


@dataclass
class Commodity:
    id: CommodityId
    name: str
    base_price: float
    perishable: bool


class CommodityRegistry:
    def __init__(self):
        self._commodities: Dict[CommodityId, Commodity] = {}

    def load_from_yaml(self, path: Path):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        for c_data in data:
            commodity = Commodity(
                id=CommodityId(c_data['id']),
                name=c_data['name'],
                base_price=c_data['base_price'],
                perishable=c_data['perishable']
            )
            self._commodities[commodity.id] = commodity

    def get(self, commodity_id: CommodityId) -> Commodity:
        if commodity_id not in self._commodities:
            raise ValueError(f"Commodity with ID '{commodity_id}' not found.")
        return self._commodities[commodity_id]

    def all_commodities(self) -> List[Commodity]:
        return list(self._commodities.values())

# Global registry instance
commodity_registry = CommodityRegistry()
