# StarSim

A space simulation engine featuring procedurally generated star systems, a supply-and-demand economy, faction AI, dynamic events, and an interactive D3.js web visualizer.

## Features

- **Procedural Universe Generation** — Star systems with typed planets (continental, desert, ocean, volcanic, ice, gas giant, etc.), each with habitability ratings and resource potentials. Trade lanes connect worlds with distance, hazard, and capacity properties.
- **Economy Engine** — Market-driven pricing, production via recipes (farming, mining, refining), population consumption with growth and unrest, inter-world trade shipping, and investment mechanics.
- **Faction AI** — Factions compete for influence and territorial control. AI evaluates worlds based on economic and military value, manages garrisons, and makes strategic decisions each tick.
- **Dynamic Events** — Condition-triggered events like food riots, ore booms, pirate raids, and diplomatic summits that affect stability, prosperity, and resource inventories.
- **Logistics** — Trade lane capacity management, active shipment tracking, and hazard-based risk on routes.
- **Web Visualizer** — Interactive Flask + D3.js force-directed graph showing faction territories, world details, and real-time simulation controls.

## Project Structure

```
StarSim/
├── src/starsim/          # Core simulation engine
│   ├── core/             #   State, IDs, simulation loop, audit logging
│   ├── economy/          #   Markets, production, consumption, trade, inventory
│   ├── factions/         #   Faction model, AI decision-making
│   ├── events/           #   Event definitions, generation, and effects
│   ├── generation/       #   Universe/planet/lane procedural generation
│   ├── world/            #   World model and YAML loading
│   ├── io/               #   JSON serialization/deserialization
│   ├── logistics/        #   Shipping routes and lane capacity
│   └── reports/          #   Gazette narratives and world summary cards
├── visualizer/           # Flask web UI with D3.js visualization
│   ├── app.py            #   Server, API endpoints, SimulationController
│   ├── templates/        #   HTML templates
│   └── static/           #   CSS and JavaScript (D3.js)
├── data/                 # YAML configuration files
│   ├── universe.yaml     #   Initial universe definition
│   ├── commodities.yaml  #   Commodity types and properties
│   ├── recipes.yaml      #   Production recipes
│   ├── events.yaml       #   Event definitions and triggers
│   └── generation/       #   Planet types, system templates, name pools
├── scripts/              # CLI utilities
│   ├── run_sim.py        #   Run the simulation headlessly
│   ├── gen_universe.py   #   Generate a random universe
│   └── inspect_world.py  #   Inspect a specific world's state
└── tests/                # Test suite (pytest)
```

## Installation

**Prerequisites:** Python 3.9+

```bash
# Clone the repository
git clone https://github.com/Aitgray/StarSim.git
cd StarSim

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install pyyaml numpy scipy flask
```

## Usage

### Web Visualizer (Interactive)

```bash
python visualizer/app.py
```

Open your browser to `http://localhost:5000`. The visualizer generates a universe and displays an interactive force-directed graph where you can:

- **Play/Pause** the simulation in real time
- **Step** forward or **Rewind** through tick history
- **Click** on worlds to view detailed resource, faction, and economic data
- **Drag** nodes to rearrange the layout

Worlds are color-coded by faction control, with a legend showing each faction.

### CLI Simulation (Headless)

Run the simulation without the web UI and view gazette reports in the terminal:

```bash
python scripts/run_sim.py --scenario data/universe.yaml --ticks 12
```

Options:

| Flag | Description | Default |
|------|-------------|---------|
| `--scenario` | Path to universe YAML file | `data/universe.yaml` |
| `--ticks` | Number of simulation steps | `12` |
| `--dump-json` | Export final state to `final_state.json` | off |
| `--debug-faction-ai <id>` | Print AI decision details for a faction | off |

### Generate a Universe

Create a procedurally generated universe:

```bash
python scripts/gen_universe.py --seed 42 --n-systems 5 --out data/universe_generated.json
```

### Inspect a World

View the detailed state of a specific world:

```bash
python scripts/inspect_world.py --world sol
python scripts/inspect_world.py --from-json final_state.json --world alpha_centauri
```

## Data Files

All game data is defined in YAML under `data/`:

| File | Contents |
|------|----------|
| `universe.yaml` | Starting worlds, lanes, factions, market state, and seed |
| `commodities.yaml` | Commodity types: energy, minerals, food, alloy, consumer goods |
| `recipes.yaml` | Production recipes: farming, mining, refining, assembly |
| `events.yaml` | Event triggers and effects: riots, booms, raids, summits |
| `generation/planet_types.yaml` | Planet archetypes with habitability and resource distributions |
| `generation/system_templates.yaml` | Star system structure templates |
| `generation/planet_names.yaml` | Name pool for generated planets |
| `generation/system_names.yaml` | Name pool for generated star systems |

## Development

### Running Tests

```bash
pytest
```

The test suite covers economy, factions, generation, events, serialization, and regression scenarios (72 tests).

### Linting and Formatting

```bash
ruff check .          # Lint
ruff format --check . # Check formatting
ruff format .         # Auto-format
```

### Type Checking

```bash
mypy .
```

### CI

GitHub Actions runs all checks (ruff, mypy, pytest) on Python 3.9, 3.10, and 3.11 for every push and pull request.

## Tech Stack

- **Python 3.9+** — Core simulation engine
- **Flask** — Web server and REST API
- **D3.js v7** — Force-directed graph visualization
- **NumPy / SciPy** — Lane generation (Delaunay triangulation)
- **PyYAML** — Configuration and data loading
- **Ruff** — Linting and formatting
- **mypy** — Static type checking
- **pytest** — Testing
