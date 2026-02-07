Below is an actionable, component-by-component build plan designed to be **LLM/agent-readable**. It assumes Python, small scale (dozens of worlds), and prioritizes **determinism, testability, data-driven content, and safe extensibility**. It is structured as a sequence of milestones with: objective, deliverables, interfaces, tests (unit + integration), and “done when” criteria.

---

## Milestone 13 — Canonical Resource Model (5 primary types)

### Objective

Standardize the resource layer to the five primary Stellaris-like resources:

* **Energy** (currency / baseline utility)
* **Minerals** (construction inputs; refinery input)
* **Food** (population sustain/growth)
* **Alloy** (military construction)
* **Consumer Goods** (QoL; stability buffer; partially “burns off”)

### Deliverables

* `economy/resources.py` (or update `commodities.yaml` + `commodities.py`)

  * Define canonical IDs: `energy`, `minerals`, `food`, `alloy`, `consumer_goods`
  * Mark metadata:

    * `category`: basic / refined / military / welfare
    * `is_currency`: energy = true
    * `decay/consumption_behavior`: consumer goods partial burn
* Migrate any existing commodity usage to these IDs (or define a compatibility mapping layer).

### Tests

* Unit: commodity registry loads and contains exactly the five primary resources (plus any optional extras if you allow them).
* Integration: existing scenario still loads; if incompatible, create `data/scenarios/v2_*` and add a migration note.

### Done when

* The sim runs with these resources without crashes and prices/inventories exist for them.

---

## Milestone 14 — Population Food Constraint + Growth/Decline

### Objective

Make **food** a hard constraint on population sustain and growth.

### Mechanics (simple, table-friendly)

* Each world with population has:

  * `food_required_per_tick = pop_size * rate`
  * If food available < required:

    * apply shortage ratio → **population declines**
    * optionally increases unrest / reduces stability
  * If food available ≥ required:

    * population grows at base growth rate, modulated by stability/prosperity

### Deliverables

* Update `economy/consumption.py`:

  * food requirement explicit
  * population delta computed deterministically
* Add a world pressure metric: `food_balance` and/or `starvation_level`

### Tests

* Unit:

  * insufficient food decreases population
  * sustained sufficient food increases population within bounds
* Integration:

  * in a scenario with one food producer and one consumer, trade can prevent decline.

### Done when

* In gazette output, food shortages cause population decline with clear audit log reasons.

---

## Milestone 15 — Consumer Goods QoL + Stability Buffer + Partial Burn

### Objective

Implement consumer goods as “semi-required + stability amplifier” with partial overconsumption.

### Mechanics (GM-friendly)

Per tick:

1. Consumer goods have a **baseline requirement** (small) like food but not lethal:

   * shortage reduces stability/prosperity mildly, increases unrest
2. If supply exceeds baseline:

   * apply **stability bonus** based on “excess per capita”
   * *burn off* some fraction of excess (so stockpiles don’t grow without bound)

### Deliverables

* `economy/consumption.py` updates:

  * `consumer_goods_required_per_tick`
  * `consumer_goods_excess_burn_rate` (e.g. 30–60% of excess)
* `world/model.py` / pressure model:

  * incorporate “standard of living” effect on stability

### Tests

* Unit:

  * excess consumer goods raises stability (bounded)
  * excess is partially consumed (inventory decreases)
* Integration:

  * if trade supplies consumer goods, stability improves over several ticks.

### Done when

* Consumer goods behave as a stabilizer and don’t accumulate infinitely.

---

## Milestone 16 — Minerals Refining Chains → Alloy and Consumer Goods

### Objective

Implement the Stellaris-like refinement pathways:

* Minerals → Alloy
* Minerals → Consumer Goods

…and ensure **energy** is the settlement/currency layer (your “prices” can be denominated in energy).

### Deliverables

* `data/recipes.yaml` new recipes:

  * `refine_alloy`: inputs `{minerals: x, energy: y}` outputs `{alloy: z}`
  * `refine_consumer_goods`: inputs `{minerals: x, energy: y}` outputs `{consumer_goods: z}`
* Update `economy/production.py` to support recipes involving energy.
* Confirm `market.prices` are “energy per unit” (if you already have generic prices, just ensure energy is the numeraire in reporting).

### Tests

* Unit:

  * recipe conversion respects input constraints
  * energy input matters (no free refining)
* Integration:

  * mineral-rich world becomes alloy exporter when it has refinery capacity.

### Done when

* Refining produces believable downstream effects and shows up in trade.

---

## Milestone 17 — Construction Budgeting (Minerals civilian / Alloys military)

### Objective

Add a minimal “construction economy” without turning this into a city builder.

### Mechanics

* Each world has a per-tick **build budget**:

  * civilian projects consume **minerals** (and maybe energy upkeep)
  * military projects consume **alloys**
* You do not need a full building placement system. Track:

  * `civilian_infrastructure_level` (mining, research, refining capacity)
  * `military_infrastructure_level` (starbase, shipyard capacity)
* Investments increase production caps, lane capacity, hazard reduction, etc.

### Deliverables

* `economy/investment.py`:

  * `invest_civilian(world)` consumes minerals → increases selected industry caps
  * `invest_military(world)` consumes alloys → increases garrison/defense/ship output proxy
* Hook faction AI to prefer alloy investment during wars.

### Tests

* Unit:

  * investments consume correct resources
  * caps increase deterministically and are bounded
* Integration:

  * a peaceful faction invests in civilian; wartime shifts to military.

### Done when

* Construction ties directly into your existing production/faction systems.

---

## Milestone 18 — Energy as Currency and “Tax/Upkeep” Hooks

### Objective

Make energy functionally central: most actions/maintenance require energy, and it acts as the “economic blood.”

### Mechanics (minimal, useful)

* Each world has:

  * `energy_upkeep` for population + infrastructure + garrisons
* If energy deficit:

  * stability/prosperity down, production caps throttled
* Optional: factions can “tax” controlled worlds (energy siphon to faction budget).

### Deliverables

* `economy/upkeep.py`:

  * `apply_upkeep(world)` consumes energy, applies penalties if short
* `factions/integrate.py`:

  * control grants faction `energy_income` (optional but strong for strategy)

### Tests

* Unit: energy deficits reduce output/stability deterministically
* Integration: faction with many worlds can fund more ops because of tax income

### Done when

* Energy meaningfully appears in “why things happened” logs.

---

# Procedural System/Planet Generator

## Milestone 19 — Generator Data Schema (Plaintext, Weighted)

### Objective

Define a plaintext (YAML) template schema for system/planet generation: planet types, habitability bands, and resource potentials.

### Required data files

* `data/generation/planet_types.yaml`
* `data/generation/habitability_tables.yaml`
* `data/generation/system_templates.yaml` (optional: system archetypes)

### Template requirements (what you asked for)

For each planet type:

* `weight` (how often it appears)
* `habitability_distribution` (or a set of weighted bands)
* resource potentials **dependent on habitability**:

  * two (or more) tables per type, e.g. `habitable` vs `inhospitable`
  * each table provides ranges or weighted bins for:

    * energy, minerals, food, alloy, consumer_goods (as “extractable potential”)

### Deliverables

* `generation/schema.md` describing YAML shape (for your future self + agent)
* `generation/load.py` to parse and validate tables

### Tests

* Unit: schema validation catches missing fields, invalid weights, invalid ranges
* Integration: generator loads tables and can sample 100 planets without errors

### Done when

* You have a stable, validated template format.

---

## Milestone 20 — Planet Stat Model (Habitability + Resource Potential)

### Objective

Add planet-level attributes that the economy can use:

* `habitability` (0–1)
* `resource_potential` (per resource)
* optionally `planet_size`, `features/tags`

### Deliverables

* `world/model.py` extend:

  * `World` gains `planets: list[Planet]` OR treat each planet as a sub-entity
* `generation/model.py`:

  * `Planet`: type, habitability, potentials dict, tags
* Decide how economy uses this:

  * simplest: world’s “industry caps” derive from planet potentials

### Tests

* Unit: planet potentials reflect habitability table selection
* Integration: generated world converts potentials into initial production caps

### Done when

* A generated system produces worlds with sensible resource profiles.

---

## Milestone 21 — System Generator (Create N Systems Deterministically)

### Objective

Generate star systems with a random number of planets, using weighted tables and deterministic seed.

### Mechanics

* `generate_system(seed, template_id)`:

  1. roll planet count based on system template
  2. for each planet:

     * sample planet type weighted
     * sample habitability from that type’s distribution
     * choose correct resource potential table (based on habitability thresholds)
     * sample potentials from weighted bins or ranges
  3. aggregate planets into world-level properties

### Deliverables

* `generation/system_gen.py` with:

  * `generate_world(world_id, rng, template) -> World`
  * `generate_universe(rng, n_systems) -> UniverseState` (optional)
* CLI: `scripts/gen_universe.py --seed --n --out data/universe_generated.yaml`

### Tests

* Determinism: same seed => identical generated YAML
* Distribution sanity: over many rolls, planet types approximate weights (allow tolerance)

### Done when

* You can generate a universe YAML and load it into the sim without manual edits.

---

## Milestone 22 — Economy Bootstrap From Generated Potentials

### Objective

Turn planet potentials into actual starting state:

* initial inventories
* production capacities
* population/habitability relationship

### Rules (simple + Stellaris-flavored)

* Habitability impacts:

  * base stability/prosperity
  * population growth cap
  * effective output multiplier on food/consumer goods
* Potentials map to industry caps:

  * minerals potential -> mining cap
  * food potential -> farming cap
  * energy potential -> generator cap
  * optional: allow refining (minerals -> alloys/CG) based on tech or infra

### Deliverables

* `generation/bootstrap.py`:

  * `apply_planet_potentials_to_world(world)`:

    * set baseline production caps and/or inventories
    * set default population size based on habitability

### Tests

* Unit: higher habitability yields higher sustainable population/growth
* Integration: generated worlds don’t instantly starve unless designed to

### Done when

* Generated universes run for 24 ticks with plausible stability and trade.

---

## Milestone 23 — Reports: Stellaris-style Resource + Stability Summary

### Objective

Make the output GM-useful: “resource ledger” per world and faction.

### Deliverables

* `reports/world_cards.py` add:

  * net monthly income/deficit per resource
  * food balance and pop trend
  * stability changes due to consumer goods, unrest, energy upkeep
* `reports/gazette.py` add:

  * top 3 shortages (by severity)
  * top 3 booms (by surplus)
  * major faction shifts linked to resource drivers

### Tests

* Snapshot/regression: report format stable and includes required fields.

### Done when

* You can read one page and improvise session hooks.

---

## Milestone 24 — Regression Packs for Generator + Resource Economy

### Objective

Protect against future refactors breaking generation or economic dynamics.

### Deliverables

* `tests/test_generator_regression.py`

  * generate universe with seed X
  * compare hash/normalized output of world list + planet summaries
* `tests/test_resource_economy_regression.py`

  * run scenario for N ticks and assert stable invariants:

    * no negative inventories
    * population doesn’t explode without food
    * consumer goods excess doesn’t grow unbounded

### Done when

* You can safely tweak tables and immediately see intended vs unintended drift.

---

# YAML Template Sketch (for your weighted tables)

This is intentionally “agent-friendly” and mod-friendly.

```yaml
# data/generation/planet_types.yaml
planet_types:
  - id: continental
    weight: 12
    habitability:
      # weighted bands -> sample uniform within band
      - band: [0.70, 0.95]
        weight: 70
      - band: [0.50, 0.70]
        weight: 25
      - band: [0.20, 0.50]
        weight: 5

    resource_tables:
      habitable:
        when_habitability_gte: 0.60
        potentials:
          energy: {range: [1, 4]}
          minerals: {range: [1, 3]}
          food: {range: [2, 6]}
          alloy: {range: [0, 1]}
          consumer_goods: {range: [1, 3]}
      inhospitable:
        when_habitability_lt: 0.60
        potentials:
          energy: {range: [1, 3]}
          minerals: {range: [1, 4]}
          food: {range: [0, 2]}
          alloy: {range: [0, 1]}
          consumer_goods: {range: [0, 2]}
```

If you prefer *weighted bins* instead of ranges:

```yaml
potentials:
  minerals:
    bins:
      - value: 0
        weight: 10
      - value: 1
        weight: 30
      - value: 2
        weight: 35
      - value: 3
        weight: 20
      - value: 4
        weight: 5
```

This makes distribution shaping easier than random ranges.

---

# CI/CD Additions

* CI already runs lint/type/test.
* Add a nightly (optional) workflow:

  * run generator distribution sanity test with more samples (slower)
* Add a `make regen-fixtures` (or script) to intentionally update regression snapshots when you change the model.

---

If you want the plan to be even more “agent-executable,” I can rewrite it into a strict checklist format with:

* exact file names to edit/create per milestone
* exact function signatures
* exact test names and assertions (including tolerances for distribution tests)

