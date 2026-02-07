# Generation Data Schema

This document describes the YAML schema for defining planet types, habitability distributions, and resource potentials for procedural generation in StarSim.

---

## `data/generation/planet_types.yaml`

This file defines various planet types and their characteristics.

### Top-level Structure

A list of planet type definitions.

```yaml
planet_types:
  - # Planet Type Definition 1
  - # Planet Type Definition 2
  # ...
```

### Planet Type Definition (`- id: continental`)

```yaml
- id: "continental"              # (string, required) Unique identifier for the planet type.
  name: "Continental World"      # (string, required) Human-readable name.
  weight: 12                     # (integer, required) Relative weight for random selection during generation. Higher weight means more common.
  habitability_distribution:     # (list of objects, required) Defines how habitability is distributed for this planet type.
    - band: [0.70, 0.95]         # (list of 2 floats, required) [min_habitability, max_habitability] for this band.
      weight: 70                 # (integer, required) Relative weight for selecting this band.
    - band: [0.50, 0.70]
      weight: 25
    - band: [0.20, 0.50]
      weight: 5
  resource_tables:               # (object, required) Defines resource potentials based on habitability thresholds.
    habitable:                   # (object, required) Resource potentials for highly habitable planets of this type.
      when_habitability_gte: 0.60 # (float, required) Apply this table if habitability is >= this value.
      potentials:                # (object, required) Defines resource potential ranges or bins.
        energy: {range: [1, 4]}  # (object, required) Resource potential definition. Can be 'range' or 'bins'.
        minerals: {range: [1, 3]}
        food: {range: [2, 6]}
        alloy: {range: [0, 1]}
        consumer_goods: {range: [1, 3]}
    inhospitable:                # (object, required) Resource potentials for less habitable planets of this type.
      when_habitability_lt: 0.60  # (float, required) Apply this table if habitability is < this value.
      potentials:
        energy: {range: [1, 3]}
        minerals: {range: [1, 4]}
        food: {range: [0, 2]}
        alloy: {range: [0, 1]}
        consumer_goods: {range: [0, 2]}
```

### Resource Potential Definition (`energy: {range: [1, 4]}` or `minerals: {bins: [...]}`)

Can be either a `range` or `bins`:

#### Range-based Potential

```yaml
energy: {range: [min_value, max_value]} # (list of 2 integers, required) Sample uniformly between min_value and max_value (inclusive).
```

#### Bins-based Potential

```yaml
minerals:
  bins:                          # (list of objects, required) Defines weighted bins for resource potential values.
    - value: 0                   # (integer, required) The potential value.
      weight: 10                 # (integer, required) Relative weight for selecting this bin.
    - value: 1
      weight: 30
    - value: 2
      weight: 35
    - value: 3
      weight: 20
    - value: 4
      weight: 5
```

---

## `data/generation/habitability_tables.yaml` (Optional - for global modifiers)

Currently minimal, as habitability distributions are integrated into `planet_types.yaml`. Can be extended for global rules.

```yaml
# Empty for now, or contains global habitability rules
```

---

## `data/generation/system_templates.yaml`

Defines archetypes for generating entire star systems.

### Top-level Structure

A list of system template definitions.

```yaml
system_templates:
  - # System Template Definition 1
  - # System Template Definition 2
  # ...
```

### System Template Definition (`- id: default_system`)

```yaml
- id: "default_system"           # (string, required) Unique identifier for the system template.
  name: "Default Star System"    # (string, required) Human-readable name.
  min_planets: 2                 # (integer, required) Minimum number of planets to generate in this system.
  max_planets: 5                 # (integer, required) Maximum number of planets to generate in this system.
  planet_type_weights:           # (object, required) Overrides or references weights for planet types from `planet_types.yaml`.
    continental: 1.0             # (float, optional) Multiplier for 'continental' planet type's base weight.
    desert: 1.0
    ocean: 1.0
    # ... other planet types
```
