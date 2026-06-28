# Autoresearch Self-Improvement Loop

Turns `Body._self_improvement_cycle()` from a stub into a real autonomous
experimentation system. The ecosystem proposes changes to its own parameters,
runs fixed-budget experiments, keeps improvements, and reverts regressions —
inspired by karpathy/autoresearch, applied to *agent behaviour parameters*
rather than model weights.

## Status

✅ Implemented on `feature/autoresearch`. 16 new tests; full suite 217 passing.
Additive — a Body with no engine attached behaves exactly as before.

## Module map (`src/autoresearch/`)

| File | Role |
|------|------|
| `contracts.py` | `ExperimentType`, `ExperimentProposalV0`, `ExperimentResultV0`, `ImprovementCycleV0` (shell) |
| `evaluator.py` | `EcosystemEvaluator` — single-scalar ecosystem fitness |
| `proposer.py` | `Proposer` (guarded proposal generation) + `Checkpointer` (non-destructive revert) |
| `runner.py` | `AutoResearchEngine` — the experiment loop |
| `integration.py` | `build_engine()`, `attach_to_body()` |

## The experiment loop

```
run_cycle(env):
  1. propose a single guarded parameter change
  2. measure baseline fitness over N ticks (old value)
  3. apply the change
  4. measure fitness over N ticks (new value)
  5. delta > threshold ? commit : roll back
  6. record ImprovementCycleV0 in the Mouseion (topic: "autoresearch")
```

Fitness is averaged across the window so the commit/revert decision is robust to
single-tick noise.

## Experiment types

| Type | Target | Revert |
|------|--------|--------|
| `NICHE_URGENCY_GROWTH` | one niche's `urgency_growth_rate` | restore value |
| `ENERGY_REGEN` | `Environment.resource_regen_rate` | restore value |
| `CARRYING_CAPACITY` | `Selector.carrying_capacity` | restore value |
| `SELECTION_STRENGTH` | `Selector.selection_strength` | restore value |
| `MUTATION_RATE` | `Mutator.base_rate` | restore value |

Only the types whose components were supplied are offered (e.g. mutation-rate
experiments require a `Mutator`).

## Ecosystem fitness

`EcosystemEvaluator.score(env)` ∈ [0, 1] combines:

```
0.40 · mean agent fitness   (reuses the existing FitnessEvaluator)
0.25 · knowledge growth      (records added this window, normalised)
0.20 · energy headroom       (pool / initial)
0.15 · niche fill rate
```

## Compassion guard

Compassion is a first-class architectural value, so the proposer rejects any
change that would plausibly harm agents — *before* it ever runs:

| Guard | Reject when |
|-------|-------------|
| starvation | `energy_regen < 0.005` |
| lethal selection | `selection_strength > 0.6` |
| destabilisation | `mutation_rate > 0.25` |
| population collapse | `carrying_capacity < 2` |

`Proposer.propose()` only ever returns proposals that pass the guard.

## Wiring into a Body

```python
from src.autoresearch import build_engine, attach_to_body

engine = build_engine(selector=selector, mutator=mutator,
                      initial_energy=8000.0, experiment_ticks=6)
attach_to_body(body, engine)
# body.step(env) now runs a real experiment every 20 ticks
```

A Body without an attached engine keeps its original fitness-history behaviour
(no change to existing callers or tests).

## Demo

```bash
python examples/autoresearch_demo.py
```

Runs 12 self-improvement cycles over a 20-agent colony, committing improvements
and reverting regressions, with every experiment logged to the Mouseion.
