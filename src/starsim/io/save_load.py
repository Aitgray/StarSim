import json
from typing import Dict, Any, defaultdict

from ..core.ids import WorldId, LaneId, CommodityId, RecipeId, FactionId # Import FactionId
from ..core.state import UniverseState
from ..world.model import World, Lane
from ..economy.market import Market
from ..economy.inventory import Inventory
from ..economy.consumption import Population
from ..economy.production import Industry
from ..logistics.shipping import Shipment
from ..logistics.capacity import LaneCapacity
from ..factions.model import Faction, WorldFactionState # Import Faction, WorldFactionState
from ..events.model import EventDef # Import EventDef
from ..events.registry import EventRegistry # Import EventRegistry


def to_dict(state: UniverseState) -> Dict[str, Any]:
    """Converts the UniverseState to a dictionary for serialization."""
    worlds_data = []
    for world in state.worlds.values():
        world_dict = {
            "id": world.id,
            "name": world.name,
            "stability": world.stability,
            "prosperity": world.prosperity,
            "tech": world.tech,
            "tags": list(world.tags),
            "scarcity": world.scarcity,
            "unrest": world.unrest,
        }
        if world.market:
            world_dict["market"] = {
                "inventory": world.market.inventory.to_dict(),
                "prices": {c_id: price for c_id, price in world.market.prices.items()},
                "targets": {c_id: target for c_id, target in world.market.targets.items()},
            }
        if world.population:
            world_dict["population"] = {
                "size": world.population.size,
                "growth_rate": world.population.growth_rate,
                "needs": {c_id: qty for c_id, qty in world.population.needs.items()},
            }
        if world.industry:
            world_dict["industry"] = {
                "caps": {r_id: cap for r_id, cap in world.industry.caps.items()},
            }
        if world.factions:
            world_dict["factions"] = {
                "influence": {f_id: inf for f_id, inf in world.factions.influence.items()},
                "garrison": {f_id: gar for f_id, gar in world.factions.garrison.items()},
                "control": world.factions.control,
                "control_threshold_gain": world.factions.control_threshold_gain,
                "control_threshold_loss": world.factions.control_threshold_loss,
            }
        worlds_data.append(world_dict)

    lanes_data = [
        {
            "id": lane.id,
            "a": lane.a,
            "b": lane.b,
            "distance": lane.distance,
            "hazard": lane.hazard,
            "capacity": lane.capacity,
        }
        for lane in state.lanes.values()
    ]

    shipments_data = [
        {
            "commodity_id": shipment.commodity_id,
            "quantity": shipment.quantity,
            "source_world_id": shipment.source_world_id,
            "destination_world_id": shipment.destination_world_id,
            "eta_tick": shipment.eta_tick,
            "lane_id": shipment.lane_id,
        }
        for shipment in state.active_shipments
    ]

    lane_capacity_data = {
        str(lane_id): capacity for lane_id, capacity in state.lane_capacity_tracker.used_capacity.items()
    }

    factions_data = [
        {
            "id": faction.id,
            "name": faction.name,
            "traits": list(faction.traits),
            "weights": faction.weights,
        }
        for faction in state.factions.values()
    ]

    events_data = [
        {
            "id": event_def.id,
            "base_weight": event_def.base_weight,
            "conditions": event_def.conditions,
            "effects": event_def.effects,
        }
        for event_def in state.event_registry.all_events()
    ]

    return {
        "seed": state.seed,
        "tick": state.tick,
        "worlds": worlds_data,
        "lanes": lanes_data,
        "active_shipments": shipments_data,
        "lane_capacity_tracker": lane_capacity_data,
        "factions": factions_data,
        "event_registry": events_data,
    }


def from_dict(data: Dict[str, Any]) -> UniverseState:
    """Creates a UniverseState from a dictionary."""
    factions = {}
    if 'factions' in data:
        for f_data in data['factions']:
            faction = Faction(
                id=FactionId(f_data['id']),
                name=f_data['name'],
                traits=set(f_data.get('traits', [])),
                weights=f_data.get('weights', {}),
            )
            factions[faction.id] = faction

    worlds = {}
    for w_data in data['worlds']:
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

        world_factions = None
        control = None # Initialize control to None
        if 'factions' in w_data and w_data['factions'] is not None:
            wf_data = w_data['factions']
            influence = {FactionId(f_id): inf for f_id, inf in wf_data.get('influence', {}).items()}
            garrison = {FactionId(f_id): gar for f_id, gar in wf_data.get('garrison', {}).items()}
            control = FactionId(wf_data['control']) if wf_data.get('control') else None
            world_factions = WorldFactionState(
                influence=influence,
                garrison=garrison,
                control=control,
                control_threshold_gain=wf_data.get('control_threshold_gain', 0.7),
                control_threshold_loss=wf_data.get('control_threshold_loss', 0.4),
            )

        worlds[WorldId(w_data['id'])] = World(
            id=WorldId(w_data['id']),
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
            factions=world_factions,
            control=control, # Set world.control from world_factions.control
        )

    lanes = {
        LaneId(l_data['id']): Lane(
            id=LaneId(l_data['id']),
            a=WorldId(l_data['a']),
            b=WorldId(l_data['b']),
            distance=l_data.get('distance', 1.0),
            hazard=l_data.get('hazard', 0.0),
            capacity=l_data.get('capacity', 1.0),
        ) for l_data in data['lanes']
    }

    active_shipments = []
    if 'active_shipments' in data:
        for s_data in data['active_shipments']:
            shipment = Shipment(
                commodity_id=CommodityId(s_data['commodity_id']),
                quantity=s_data['quantity'],
                source_world_id=WorldId(s_data['source_world_id']),
                destination_world_id=WorldId(s_data['destination_world_id']),
                eta_tick=s_data['eta_tick'],
                lane_id=s_data.get('lane_id'),
            )
            active_shipments.append(shipment)

    lane_capacity_tracker = LaneCapacity()
    if 'lane_capacity_tracker' in data:
        lane_capacity_tracker.used_capacity = {
            LaneId(str_id): capacity for str_id, capacity in data['lane_capacity_tracker'].items()
        }

    event_registry = EventRegistry()
    if 'event_registry' in data:
        for e_data in data['event_registry']:
            event_def = EventDef(
                id=e_data['id'],
                base_weight=e_data.get('base_weight', 1.0),
                conditions=e_data.get('conditions', []),
                effects=e_data.get('effects', [])
            )
            event_registry._events[event_def.id] = event_def

    state = UniverseState(
        seed=data['seed'],
        tick=data['tick'],
        worlds=worlds,
        lanes=lanes,
        active_shipments=active_shipments,
        lane_capacity_tracker=lane_capacity_tracker,
        factions=factions,
        event_registry=event_registry,
    )
    return state


def save_to_json(state: UniverseState, path: str):
    """Saves the universe state to a JSON file."""
    with open(path, 'w') as f:
        json.dump(to_dict(state), f, indent=2)


def load_from_json(path: str) -> UniverseState:
    """Loads the universe state from a JSON file."""
    with open(path, 'r') as f:
        data = json.load(f)
    return from_dict(data)
