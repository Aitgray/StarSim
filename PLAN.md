Below is an actionable, component-by-component build plan designed to be **LLM/agent-readable**. It assumes Python, small scale (dozens of worlds), and prioritizes **determinism, testability, data-driven content, and safe extensibility**. It is structured as a sequence of milestones with: objective, deliverables, interfaces, tests (unit + integration), and “done when” criteria.

---

# StarSim Build Plan (Agent-Executable)

## Global Constraints (apply to every milestone)

* **Deterministic simulation:** all randomness comes from `rng = random.Random(seed)` owned by `UniverseState` (no global `random` calls).
* **State is serializable:** “source of truth” is dicts keyed by string IDs; avoid deep object pointer graphs.
* **No hidden coupling:** modules communicate via explicit function inputs/outputs and well-defined dataclasses.
* **Every milestone adds tests** and keeps all tests green.
* **Logging is explainable:** every tick produces an “audit trail” of why major deltas happened.

---

## Milestone 0 — Repo + Tooling Baseline (CI/CD-ready skeleton)

### Objective

Create a project skeleton with formatting, linting, typing, tests, and CI.

### Deliverables

* `pyproject.toml` using:

  * formatter: `ruff format` (or `black`)
  * linter: `ruff`
  * type check: `mypy` (optional but recommended)
  * tests: `pytest`
* `src/starsim/` package scaffold
* GitHub Actions workflow:

  * run `ruff`, `mypy`, `pytest` on PR/push
* pre-commit config (optional but recommended):

  * ruff, formatting, trailing whitespace, end-of-file, etc.

### Tests

* Smoke test: `pytest -q` runs and passes with one trivial test.

### Done when

* `git push` triggers CI; CI passes.
* `pip install -e .` works.

---

## Milestone 1 — Core Types + State Container

### Objective

Define the minimal state model with ID registries and deterministic RNG.

### Deliverables

* `core/ids.py`: type aliases `WorldId`, `LaneId`, `CommodityId`, `FactionId`

* `core/rng.py`: wrapper or helper for seeded RNG

* `core/state.py`:

  * `UniverseState` with:

    * `seed: int`
    * `tick: int`
    * `rng: random.Random`
    * `worlds: dict[WorldId, World]`
    * `lanes: dict[LaneId, Lane]`
    * `adj: dict[WorldId, list[LaneId]]` (derived)
  * methods:

    * `rebuild_adjacency()`
    * `neighbors(world_id) -> list[WorldId]`
    * `lanes_from(world_id) -> list[Lane]`

* `world/model.py`:

  * `World` dataclass with:

    * `id`, `name`
    * core stats: `stability`, `prosperity`, `tech`
    * `tags: set[str]`
    * optional components: `market: Market|None`, `population: Population|None`, etc. (can be placeholders now)
  * `Lane` dataclass:

    * `id`, `a`, `b`
    * `distance`, `hazard`, `capacity`

### Tests

* Unit:

  * adjacency rebuild correctness
  * `neighbors()` returns expected IDs
* Determinism:

  * same seed → same first 10 RNG draws (through state-owned RNG)

### Done when

* You can create a tiny state in-memory, rebuild adjacency, and query neighbors with tests passing.

---

## Milestone 2 — Serialization + Scenario Loading (Data-driven)

### Objective

Load a universe from YAML/JSON and save/load state snapshots.

### Deliverables

* `world/load.py`

  * load functions:

    * `load_universe(path) -> UniverseState`
  * schema checks (hard errors):

    * unknown world referenced by a lane
    * duplicate IDs

* `io/save_load.py`

  * `to_dict(state) -> dict`
  * `from_dict(d) -> UniverseState`
  * JSON round-trip support

* `data/universe.yaml` minimal sample (3 worlds, 3 lanes)

### Tests

* Unit:

  * YAML load produces correct world/lane counts
  * invalid lane reference raises error
* Integration:

  * load → save → load results in equivalent state (ignoring derived adjacency)

### Done when

* You can edit YAML to add a planet and re-run tests; nothing breaks.

---

## Milestone 3 — Simulation Engine + Audit Log

### Objective

Create the tick loop with a stable step ordering and structured logs.

### Deliverables

* `core/sim.py`

  * `step(state: UniverseState) -> TickReport`
  * fixed order (placeholder stages):

    1. economy.production
    2. economy.consumption
    3. economy.trade
    4. economy.prices
    5. factions.step
    6. events.roll
* `core/log.py`

  * `AuditLog` accumulating entries:

    * `type`, `world_id`, `faction_id`, `delta`, `reason`, `details`
* `reports/gazette.py`

  * text summary from audit log

### Tests

* Unit:

  * `step()` increments tick exactly once
  * log entries appear when placeholder actions occur
* Determinism:

  * same seed + same initial state → identical TickReport content for N ticks

### Done when

* Running `scripts/run_sim.py --ticks 12` prints a repeatable gazette.

---

## Milestone 4 — Commodities + Market Component (Heuristic pricing)

### Objective

Implement commodities, inventories, and price adjustment rules.

### Deliverables

* `economy/commodities.py`

  * commodity registry loaded from `data/commodities.yaml`
* `economy/inventory.py`

  * `Inventory` as `dict[CommodityId, float]` + helpers:

    * `get(qty=0 default)`, `add`, `remove_clamped`
* `economy/market.py`

  * `Market` component:

    * `inventory`, `prices`, `targets` (days-of-cover target per commodity)
  * `update_prices(world, state)`:

    * compare inventory to target cover; adjust via bounded multiplier

### Tests

* Unit:

  * price increases when inventory below target
  * price decreases when inventory above target
  * price remains within bounds (min/max clamp)
* Integration:

  * add a world with missing prices → defaults set without crash

### Done when

* A world with a Market shows believable price motion over repeated ticks.

---

## Milestone 5 — Population + Consumption (needs → pressure)

### Objective

Add population demand and shortage-driven instability.

### Deliverables

* `economy/consumption.py`

  * `Population` component:

    * `size`, `growth_rate`, `needs: dict[CommodityId, float]`
  * `consume(world)`:

    * remove from market inventory according to needs
    * compute `shortage_ratio` per commodity
* `world/model.py` add:

  * `pressure: dict[str, float]` or explicit fields:

    * `scarcity`, `unrest`
* `events` placeholder: “shortage increases unrest”

### Tests

* Unit:

  * if inventory insufficient, shortage ratio > 0
  * shortage increases unrest, decreases stability (bounded)
* Integration:

  * two ticks with no food → instability worsens deterministically

### Done when

* You see food/medicine shortages translate into world-level pressures.

---

## Milestone 6 — Production (recipes + capacity)

### Objective

Implement industries that turn inputs into outputs with capacities.

### Deliverables

* `economy/recipes.py` from `data/recipes.yaml`
* `economy/production.py`

  * `Industry` component:

    * `caps: dict[RecipeId, float]`
  * `produce(world)`:

    * for each recipe:

      * compute max feasible by available inputs + cap
      * consume inputs, add outputs

### Tests

* Unit:

  * production limited by input availability
  * production limited by capacity
  * no negative inventory
* Integration:

  * an “agri world” produces food over time and stabilizes itself

### Done when

* Worlds can be set up as producers/consumers and behave sensibly.

---

## Milestone 7 — Trade + Logistics (simple arbitrage)

### Objective

Move goods between worlds based on profit, distance, hazard, and capacity.

### Deliverables

* `logistics/shipping.py`

  * `Shipment`: commodity, qty, src, dst, eta_tick

* `economy/trade.py`

  * build candidate trades along direct neighbor lanes:

    * if `price_dst - price_src - shipping_cost > threshold`
  * create shipments (respect lane capacity)
  * arrivals add to dst inventory at eta

* `logistics/capacity.py`

  * track per-lane used capacity per tick

### Tests

* Unit:

  * profitable trades create shipments
  * shipments arrive after travel time
  * capacity limits prevent infinite shipping
* Integration:

  * create two worlds with price gradient; verify convergence reduces gradient over time

### Done when

* The sim generates trade flows and the economy equalizes where lanes allow.

---

## Milestone 8 — Factions Model (presence, influence, control)

### Objective

Represent faction state per world and basic control rules.

### Deliverables

* `factions/model.py`

  * `Faction`: id, name, traits, weights
  * per-world maps:

    * `influence[faction][world]`
    * `garrison[faction][world]`
    * `control[world] -> faction|None` (derived from influence with hysteresis)
* `factions/resolve.py`

  * hysteresis thresholds: gain at 0.70, lose at 0.40
  * control affects world modifiers:

    * stability bonus, tax friction, lane patrol bias (later)

### Tests

* Unit:

  * influence crossing threshold flips control
  * hysteresis prevents flip-flop
* Integration:

  * control modifies event weights or stability in a deterministic way

### Done when

* You can set starting influence in YAML and see control changes.

---

## Milestone 9 — Faction Decision Logic (greedy agent with inertia)

### Objective

Implement per-faction action selection: compute world values, pick highest ROI actions.

### Deliverables

* `factions/ai.py`

  * `compute_world_value(faction, world, state) -> float`

    * Econ: shipyards, food, industry output
    * Geo: neighbor halo, hub score (degree-based ok)
    * Symbolic: tags/capital/sacred
    * Threat: rival influence nearby
    * Cost: distance, enemy garrison, instability
  * smoothing + commitment (anti-thrashing)
* `factions/actions.py`

  * action defs:

    * `expand_influence(world)`
    * `reinforce(world)`
    * `raid_lane(lane)`
    * `patrol_lane(lane)`
    * `aid_world(world)` (optional)
* `factions/integrate.py`

  * apply action effects to:

    * influence/garrison
    * lane hazard/capacity modifiers
    * world stability/unrest

### Tests

* Unit:

  * given a known state, top action is reproducible (seeded)
  * commitment keeps target stable for N ticks
* Integration:

  * factions cause measurable lane hazard changes and economic disruption

### Done when

* A 3–8 world scenario yields a believable “frontline” and tug-of-war.

---

## Milestone 10 — Random Event System (pressure-weighted, table-driven)

### Objective

Add events that are state-dependent, not pure noise.

### Deliverables

* `events/model.py`

  * `EventDef`: id, base_weight, conditions, apply()
* `events/generator.py`

  * per world each tick:

    * compute weights from pressures + tags + faction tension
    * roll up to `k` events globally or per-world
* `events/effects.py`

  * effects change:

    * inventory (loss/spoilage)
    * stability/unrest
    * lane hazard
    * faction influence shifts
* `data/events.yaml` (table-driven definitions)

### Tests

* Unit:

  * event weights increase under relevant pressures
  * applying event produces bounded deltas
* Integration:

  * run 24 ticks; ensure at least one event fires; log shows reasons

### Done when

* Gazette includes “why this happened” events tied to state.

---

## Milestone 11 — Regression Harness + Scenario Testing

### Objective

Prevent future changes from breaking outcomes silently.

### Deliverables

* `tests/test_regression_seeded.py`

  * load a fixed scenario, run N ticks, compare:

    * selected summary metrics (not every float):

      * top 3 prices per world
      * control map
      * total trade volume
      * lane hazard distribution
* `reports/world_cards.py` for quick human inspection

### Tests

* Regression test is expected to fail only when you intentionally change model behavior.

### Done when

* You can refactor internals and trust “behavioral drift” is visible.

---

## Milestone 12 — Developer UX (CLI + debugging tools)

### Objective

Make it easy to run, inspect, and tweak.

### Deliverables

* `scripts/run_sim.py`

  * args: `--seed`, `--ticks`, `--scenario`, `--dump-json`, `--gazette`
* `scripts/inspect_world.py --world X`
* “debug mode” to print action scoring for one faction

### Tests

* CLI smoke tests (optional) or just ensure scripts import cleanly.

### Done when

* You can iterate quickly: change YAML → run → read gazette.

---

# Quality Gates (CI/CD)

## Required CI Jobs

* `ruff check`
* `ruff format --check`
* `pytest`
* (optional) `mypy`

## Required Practices

* Every PR/change:

  * updates or adds tests
  * maintains determinism for existing scenarios (unless intentionally changed)
* Prefer “pure functions” for transforms; keep state mutation localized in `apply_*` functions.

---

# Agent Execution Notes (how an LLM should work through this)

* Implement milestones strictly in order.
* After each milestone:

  1. run tests
  2. fix failing tests
  3. run `scripts/run_sim.py` for a tiny scenario and paste output into a `notes/` log (optional)
* Do not start a new milestone until:

  * all tests are green
  * `ruff` passes

---

If you want, I can also provide:

* a starter `pyproject.toml` + GitHub Actions YAML tailored for this,
* and “starter data files” (`universe.yaml`, `commodities.yaml`, `recipes.yaml`, `factions.yaml`, `events.yaml`) that produce interesting output within ~12 ticks.
