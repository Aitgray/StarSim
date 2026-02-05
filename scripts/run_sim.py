import argparse
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.starsim.world.load import load_universe
from src.starsim.core.sim import step
from src.starsim.reports.gazette import generate_gazette


def main():
    parser = argparse.ArgumentParser(description="Run the StarSim simulation.")
    parser.add_argument(
        "--scenario",
        type=str,
        default="data/universe.yaml",
        help="Path to the scenario YAML file.",
    )
    parser.add_argument(
        "--ticks", type=int, default=12, help="Number of ticks to simulate."
    )
    parser.add_argument(
        "--dump-json", action="store_true", help="Dump the final state to a JSON file."
    )
    parser.add_argument(
        "--debug-faction-ai", type=str, help="Enable AI debugging for a specific faction ID."
    )
    args = parser.parse_args()

    # Load the universe
    state = load_universe(Path(args.scenario))
    print(f"Loaded universe from '{args.scenario}' with seed {state.seed}.")

    # Run the simulation
    for _ in range(args.ticks):
        initial_tick = state.tick
        
        # Faction AI Debugging
        if args.debug_faction_ai:
            from src.starsim.factions.model import FactionId
            from src.starsim.factions.ai import select_action_debug
            
            faction_id_to_debug = FactionId(args.debug_faction_ai)
            if faction_id_to_debug in state.factions:
                debug_output = select_action_debug(state.factions[faction_id_to_debug], state)
                print(f"\n--- Faction AI Debug (Tick {initial_tick}) for {faction_id_to_debug} ---")
                print(debug_output)
            else:
                print(f"\nWarning: Debug faction '{faction_id_to_debug}' not found.")

        report = step(state)
        gazette = generate_gazette(report.log, tick=initial_tick)
        print(gazette)

    if args.dump_json:
        from src.starsim.io.save_load import save_to_json
        output_path = "final_state.json"
        save_to_json(state, output_path)
        print(f"Final state dumped to {output_path}")

if __name__ == "__main__":
    main()
