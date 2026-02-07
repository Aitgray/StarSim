import argparse
import sys
from pathlib import Path
import json

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.starsim.generation.load import load_planet_types, load_system_templates
from src.starsim.generation.system_gen import generate_universe
from src.starsim.io.save_load import save_to_json
from src.starsim.core.rng import get_seeded_rng


def main():
    parser = argparse.ArgumentParser(description="Generate a StarSim universe.")
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for universe generation.",
    )
    parser.add_argument(
        "--n-systems",
        type=int,
        default=3,
        help="Number of star systems to generate.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/universe_generated.json",
        help="Output path for the generated universe JSON file.",
    )
    args = parser.parse_args()

    # Load generation data
    planet_types_data = load_planet_types(Path("data/generation/planet_types.yaml"))
    system_templates_data = load_system_templates(Path("data/generation/system_templates.yaml"))

    # Initialize RNG
    rng = get_seeded_rng(args.seed)

    # Generate universe
    generated_universe = generate_universe(rng, args.n_systems, system_templates_data, planet_types_data)

    # Save to JSON
    save_to_json(generated_universe, args.out)
    print(f"Generated universe saved to '{args.out}'.")


if __name__ == "__main__":
    main()
