from typing import List, Optional
from collections import defaultdict

from ..core.ids import WorldId, LaneId, CommodityId
from ..core.state import UniverseState
from ..world.model import World, Lane
from ..logistics.shipping import Shipment


TRADE_THRESHOLD = 0.1 # Minimum profit margin to consider a trade


def build_candidate_trades(state: UniverseState) -> List[Shipment]:
    """
    Identifies profitable trade opportunities along direct neighbor lanes.
    """
    candidate_shipments: List[Shipment] = []

    for lane_id, lane in state.lanes.items():
        world_a = state.worlds.get(lane.a)
        world_b = state.worlds.get(lane.b)

        if not world_a or not world_b or not world_a.market or not world_b.market:
            continue

        market_a = world_a.market
        market_b = world_b.market

        for commodity in state.commodity_registry.all_commodities():
            price_a = market_a.prices.get(commodity.id)
            price_b = market_b.prices.get(commodity.id)

            if price_a is None or price_b is None:
                continue # Cannot trade if price unknown in either market

            # Calculate shipping cost (simple model: proportional to distance and hazard)
            # This should eventually be more sophisticated
            shipping_cost_per_unit = state.commodity_registry.get(commodity.id).base_price * (lane.distance * 0.01 + lane.hazard * 0.05)

            # Check for arbitrage from A to B
            profit_a_to_b = price_b - price_a - shipping_cost_per_unit
            if profit_a_to_b > TRADE_THRESHOLD:
                # How much to trade? For now, a fixed small amount or available surplus
                trade_qty = min(market_a.inventory.get(commodity.id), 10.0) # Trade up to 10 units
                if trade_qty > 0:
                    candidate_shipments.append(
                        Shipment(
                            commodity_id=commodity.id,
                            quantity=trade_qty,
                            source_world_id=world_a.id,
                            destination_world_id=world_b.id,
                            eta_tick=state.tick + round(lane.distance), # Simple ETA based on distance
                            lane_id=lane.id,
                        )
                    )
            
            # Check for arbitrage from B to A
            profit_b_to_a = price_a - price_b - shipping_cost_per_unit
            if profit_b_to_a > TRADE_THRESHOLD:
                trade_qty = min(market_b.inventory.get(commodity.id), 10.0)
                if trade_qty > 0:
                    candidate_shipments.append(
                        Shipment(
                            commodity_id=commodity.id,
                            quantity=trade_qty,
                            source_world_id=world_b.id,
                            destination_world_id=world_a.id,
                            eta_tick=state.tick + round(lane.distance),
                            lane_id=lane.id,
                        )
                    )
    return candidate_shipments


def process_trade(state: UniverseState, allow_new_trades: bool = True):
    """
    Processes new trade opportunities and handles arriving shipments.
    """
    # 1. Clear used capacity for this tick
    state.lane_capacity_tracker.reset()

    # 2. Identify new trades and create shipments
    if allow_new_trades:
        new_shipments = build_candidate_trades(state)
        
        for shipment in new_shipments:
            if shipment.lane_id:
                lane = state.lanes[shipment.lane_id]
                remaining_capacity = state.lane_capacity_tracker.get_remaining_capacity(shipment.lane_id, lane.capacity)
                
                if shipment.quantity <= remaining_capacity:
                    # Deduct from source inventory
                    source_world = state.worlds[shipment.source_world_id]
                    actual_deducted = source_world.market.inventory.remove_clamped(shipment.commodity_id, shipment.quantity)
                    
                    if actual_deducted > 0: # Only create shipment if goods were actually available
                        state.active_shipments.append(shipment)
                        state.lane_capacity_tracker.add_used_capacity(shipment.lane_id, actual_deducted)
                else:
                    # Trade exceeds capacity, log or handle partial trade (for now, just skip)
                    pass # TODO: handle partial shipments

    # 3. Process arriving shipments
    arrived_shipments: List[Shipment] = []
    remaining_shipments: List[Shipment] = []

    for shipment in state.active_shipments:
        if shipment.eta_tick <= state.tick:
            destination_world = state.worlds[shipment.destination_world_id]
            destination_world.market.inventory.add(shipment.commodity_id, shipment.quantity)
            arrived_shipments.append(shipment)
        else:
            remaining_shipments.append(shipment)
    
    state.active_shipments = remaining_shipments
    return arrived_shipments
