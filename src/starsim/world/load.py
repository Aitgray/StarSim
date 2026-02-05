from pathlib import Path
from typing import Dict, Any
import yaml

from ..core.ids import WorldId, LaneId, CommodityId, RecipeId
from ..core.state import UniverseState
from ..world.model import World, Lane
from ..economy.market import Market
from ..economy.inventory import Inventory
from ..economy.consumption import Population
from ..economy.production import Industry # Import Industry


class UniverseSchemaError(Exception):
    """Raised when there is a problem with the universe data schema."""
    pass


def load_universe(path: Path) -> UniverseState:
    print(f"DEBUG: Loading universe from path: {path}")
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    print(f"DEBUG: YAML data loaded: {data}")

    if data is None:
        print("DEBUG: YAML data is None, returning early.")
        return None # Explicitly return None if data is empty

    seed = data.get('seed')
    if seed is None:
        raise UniverseSchemaError("Missing 'seed' in universe data.")
    print(f"DEBUG: Seed: {seed}")

    worlds_data = data.get('worlds', [])
    lanes_data = data.get('lanes', [])
    print(f"DEBUG: Worlds data: {worlds_data}")
    print(f"DEBUG: Lanes data: {lanes_data}")

    # Schema check: duplicate IDs
    world_ids = [w['id'] for w in worlds_data]
    if len(world_ids) != len(set(world_ids)):
        raise UniverseSchemaError("Duplicate world IDs found.")
    
    lane_ids = [l['id'] for l in lanes_data]
    if len(lane_ids) != len(set(lane_ids)):
        raise UniverseSchemaError("Duplicate lane IDs found.")

    worlds = {}
    for w_data in worlds_data:
        world_id = WorldId(w_data['id'])
        market = None
        if 'market' in w_data:
            market_data = w_data['market']
            inventory = Inventory()
            for c_id, qty in market_data.get('inventory', {}).items():
                inventory.add(CommodityId(c_id), qty)
            prices = {CommodityId(c_id): price for c_id, price in market_data.get('prices', {}).items()}
            targets = {CommodityId(c_id): target for c_id, target in market_data.get('targets', {}).items()}
            market = Market(inventory=inventory, prices=prices, targets=targets)

        population = None
        if 'population' in w_data and w_data['population'] is not None:
            pop_data = w_data['population']
            needs = {CommodityId(c_id): qty for c_id, qty in pop_data.get('needs', {}).items()}
            population = Population(
                size=pop_data.get('size', 0),
                growth_rate=pop_data.get('growth_rate', 0.0),
                needs=needs,
            )

        industry = None
        if 'industry' in w_data:
            industry_data = w_data['industry']
            caps = {RecipeId(r_id): cap for r_id, cap in industry_data.get('caps', {}).items()}
            industry = Industry(caps=caps)

        worlds[world_id] = World(
            id=world_id,
            name=w_data['name'],
            stability=w_data.get('stability', 1.0),
            prosperity=w_data.get('prosperity', 1.0),
            tech=w_data.get('tech', 1.0),
            tags=set(w_data.get('tags', [])),
            scarcity=w_data.get('scarcity', 0.0),
            unrest=w_data.get('unrest', 0.0),
            market=market,
            population=population,
            industry=industry,
        )

    lanes = {}
    for l_data in lanes_data:
        # Schema check: unknown world referenced by a lane
        a_id, b_id = WorldId(l_data['a']), WorldId(l_data['b'])
        if a_id not in worlds:
            print(f"DEBUG: UniverseSchemaError - Lane '{l_data['id']}' references unknown world '{l_data['a']}'.")
            raise UniverseSchemaError(f"Lane '{l_data['id']}' references unknown world '{l_data['a']}'.")
        if b_id not in worlds:
            print(f"DEBUG: UniverseSchemaError - Lane '{l_data['id']}' references unknown world '{l_data['b']}'.")
            raise UniverseSchemaError(f"Lane '{l_data['id']}' references unknown world '{l_data['b']}'.")

        lanes[LaneId(l_data['id'])] = Lane(
            id=LaneId(l_data['id']),
            a=a_id,
            b=b_id,
            distance=l_data.get('distance', 1.0),
            hazard=l_data.get('hazard', 0.0),
            capacity=l_data.get('capacity', 1.0),
        )

    print(f"DEBUG: Worlds created: {worlds}")
    print(f"DEBUG: Lanes created: {lanes}")
    state = UniverseState(
        seed=seed,
        tick=data.get('tick', 0), # Use 0 as default if not in data
        worlds=worlds,
        lanes=lanes
    )
    print("DEBUG: UniverseState successfully created.")
    return state
