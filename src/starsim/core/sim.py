from dataclasses import dataclass

from .state import UniverseState
from .log import AuditLog
from ..economy.market import update_prices
from ..economy.consumption import consume # Import consume
from ..economy.production import produce # Import produce
from ..economy.trade import process_trade # Import process_trade
from ..factions.integrate import apply_faction_actions # Import apply_faction_actions
from ..events.generator import generate_events # Import generate_events
from ..events.effects import apply_effect # Import apply_effect


@dataclass
class TickReport:
    tick: int
    log: AuditLog


def step(state: UniverseState) -> TickReport:
    """
    Advances the simulation state by one tick.
    """
    log = AuditLog()
    
    # --- Simulation Stages ---
    
    # 1. economy.consumption
    for world in state.worlds.values():
        if world.population and world.market:
            initial_stability = world.stability
            initial_unrest = world.unrest
            consume(world, state.tick)
            if world.stability != initial_stability or world.unrest != initial_unrest:
                log.add_entry(
                    "economy.consumption.impact",
                    state.tick,
                    world_id=world.id,
                    reason=f"Consumption impact: stability changed from {initial_stability:.2f} to {world.stability:.2f}, unrest from {initial_unrest:.2f} to {world.unrest:.2f}",
                    details={"old_stability": initial_stability, "new_stability": world.stability,
                             "old_unrest": initial_unrest, "new_unrest": world.unrest}
                )
        else:
            log.add_entry("economy.consumption", state.tick, world_id=world.id, reason="No population or market, no consumption.")

    # 2. economy.production
    for world in state.worlds.values():
        if world.industry and world.market:
            initial_inventory = {c_id: qty for c_id, qty in world.market.inventory.to_dict().items()}
            produce(world, state)
            final_inventory = world.market.inventory.to_dict()

            produced_items = {c_id: final_inventory.get(c_id, 0) - initial_inventory.get(c_id, 0)
                              for c_id in set(initial_inventory) | set(final_inventory)}
            produced_items = {k: v for k, v in produced_items.items() if v != 0}
            
            if produced_items:
                log.add_entry(
                    "economy.production.output",
                    state.tick,
                    world_id=world.id,
                    reason=f"Production occurred in {world.id}",
                    details={"changes": produced_items}
                )
        else:
            log.add_entry("economy.production", state.tick, world_id=world.id, reason="No industry or market, no production.")
    
    # 3. economy.trade
    arrived_shipments = process_trade(state, allow_new_trades=True)
    if state.active_shipments:
        log.add_entry(
            "economy.trade.new_shipments",
            state.tick,
            reason=f"{len(state.active_shipments)} new shipments en route.",
            details={"shipments": [s.commodity_id for s in state.active_shipments]}
        )
    if arrived_shipments:
        log.add_entry(
            "economy.trade.arrivals",
            state.tick,
            reason=f"{len(arrived_shipments)} shipments arrived.",
            details={"arrivals": [{s.commodity_id: s.quantity} for s in arrived_shipments]}
        )
    else:
        log.add_entry("economy.trade", state.tick, reason="No active trade or arrivals.")
    
    # 4. economy.prices
    for world in state.worlds.values():
        if world.market:
            initial_prices = {c_id: price for c_id, price in world.market.prices.items()} # Capture initial state for logging
            update_prices(world, state)
            for c_id, new_price in world.market.prices.items():
                old_price = initial_prices.get(c_id, state.commodity_registry.get(c_id).base_price)
                if old_price != new_price:
                    log.add_entry(
                        "economy.prices.update", 
                        state.tick, 
                        world_id=world.id, 
                        delta=new_price - old_price, 
                        reason=f"Price of {c_id} changed from {old_price:.2f} to {new_price:.2f}.",
                        details={"commodity_id": c_id, "old_price": old_price, "new_price": new_price}
                    )
        else:
            log.add_entry("economy.prices", state.tick, world_id=world.id, reason="No market in world, no price update.")

    # 5. factions.step
    apply_faction_actions(state)
    log.add_entry("factions.step", state.tick, reason="Faction actions applied.")
    
    # 6. events.roll
    events_this_tick = generate_events(state)
    if events_this_tick:
        for event_def, target_world_id in events_this_tick:
            target_world = state.worlds[target_world_id]
            for effect in event_def.effects:
                apply_effect(effect, target_world, state)
                log.add_entry(
                    "event.triggered",
                    state.tick,
                    world_id=target_world_id,
                    reason=f"Event '{event_def.id}' triggered in {target_world_id}. Effect: {effect['type']}.",
                    details={"event_id": event_def.id, "effect": effect}
                )
    else:
        log.add_entry("events.roll", state.tick, reason="No events triggered this tick.")

    # --- End of Tick ---
    state.tick += 1
    
    return TickReport(tick=state.tick, log=log)
