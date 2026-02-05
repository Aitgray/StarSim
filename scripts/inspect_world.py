import argparse
import sys
from pathlib import Path
import json

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.starsim.world.load import load_universe
from src.starsim.io.save_load import to_dict, from_dict
from src.starsim.core.ids import WorldId


def main():
    parser = argparse.ArgumentParser(description="Inspect the state of a specific world in StarSim.")
    parser.add_argument(
        "--scenario",
        type=str,
        default="data/universe.yaml",
        help="Path to the scenario YAML file.",
    )
    parser.add_argument(
        "--world",
        type=str,
        required=True,
        help="ID of the world to inspect.",
    )
    parser.add_argument(
        "--from-json",
        type=str,
        help="Path to a JSON state file to load from instead of a YAML scenario.",
    )
    args = parser.parse_args()

    if args.from_json:
        with open(args.from_json, 'r') as f:
            data = json.load(f)
        state = from_dict(data)
        print(f"Loaded state from JSON file: {args.from_json}")
    else:
        state = load_universe(Path(args.scenario))
        print(f"Loaded universe from '{args.scenario}' with seed {state.seed}")

    world_id = WorldId(args.world)
    if world_id not in state.worlds:
        print(f"Error: World '{world_id}' not found in the universe state.")
        sys.exit(1)

    world = state.worlds[world_id]
    world_info = {
        "id": world.id,
        "name": world.name,
        "stability": world.stability,
        "prosperity": world.prosperity,
        "tech": world.tech,
        "tags": list(world.tags),
        "scarcity": world.scarcity,
        "unrest": world.unrest,
        "control": world.control,
    }
    
    if world.market:
        world_info["market"] = {
            "inventory": world.market.inventory.to_dict(),
            "prices": {c_id: price for c_id, price in world.market.prices.items()},
            "targets": {c_id: target for c_id, target in world.market.targets.items()},
        }
    if world.population:
        world_info["population"] = {
            "size": world.population.size,
            "growth_rate": world.population.growth_rate,
            "needs": {c_id: qty for c_id, qty in world.population.needs.items()},
        }
    if world.industry:
        world_info["industry"] = {
            "caps": {r_id: cap for r_id, cap in world.industry.caps.items()},
        }
    if world.factions:
        world_info["factions_component"] = {
            "influence": {f_id: inf for f_id, inf in world.factions.influence.items()},
            "garrison": {f_id: gar for f_id, gar in world.factions.garrison.items()},
            "control": world.factions.control,
        }

    print(f"\n--- World Information for '{world_id}' ---")
    print(json.dumps(world_info, indent=2))


if __name__ == "__main__":
    main()
