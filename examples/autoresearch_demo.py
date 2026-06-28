"""
examples/autoresearch_demo.py

Autoresearch self-improvement loop — demonstration.

The ecosystem proposes changes to its own parameters, runs fixed-budget
experiments, and keeps improvements while reverting regressions — all guarded by
the compassion guard (no change may starve agents or make selection lethal).

Run:
    python examples/autoresearch_demo.py
"""

from __future__ import annotations

import logging
import random

from organic_agentic_autodev.autoresearch import build_engine
from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.core.stem_cell import StemCell
from organic_agentic_autodev.evolution.mutator import Mutator
from organic_agentic_autodev.evolution.selector import Selector
from organic_agentic_autodev.mouseion.contracts import ResourceKind
from organic_agentic_autodev.mouseion.substrate import Mouseion

# Quiet per-tick logging AFTER imports (get_logger sets INFO at creation time).
for _name in ("mouseion.substrate", "environment", "stem_cell",
              "autoresearch.runner", "evolution.selector"):
    logging.getLogger(_name).setLevel(logging.ERROR)

INITIAL_ENERGY = 8000.0


def main(n_cycles: int = 12, seed: int = 42) -> None:
    rng = random.Random(seed)

    print("=" * 70)
    print("  🔬  Autoresearch Self-Improvement Demo")
    print("=" * 70)

    mouseion = Mouseion(initial_resources={ResourceKind.ENERGY: INITIAL_ENERGY})
    env = Environment(mouseion=mouseion, rng=rng)
    env.seed_niches(Environment.default_niche_set())

    # A living population so experiments have something to act on.
    for _ in range(20):
        env.register(StemCell(initial_energy=15.0,
                              rng=random.Random(rng.randint(0, 99999))))

    selector = Selector(rng=rng)
    mutator = Mutator(rng=rng)
    engine = build_engine(selector=selector, mutator=mutator,
                          initial_energy=INITIAL_ENERGY,
                          experiment_ticks=6, rng=rng)

    print(f"\n  Population: {env.agent_count()} agents | "
          f"niches: {len(env.open_niches())}")
    print(f"  Experiment types available: "
          f"{[t.value for t in engine._proposer.available_types()]}\n")

    print("  ── Running self-improvement cycles ──")
    for i in range(1, n_cycles + 1):
        cycle = engine.run_cycle(env)
        if cycle.result and cycle.proposal:
            verdict = "✅ COMMIT" if cycle.result.committed else "↩ revert"
            print(f"  Cycle {i:2d} | {cycle.proposal.experiment_type.value:<22} "
                  f"Δ={cycle.result.delta:+.4f}  {verdict}")
        else:
            note = cycle.notes.get("status", "no experiment")
            print(f"  Cycle {i:2d} | {note}")

    print("\n  ── Summary ──")
    s = engine.summary()
    for k, v in s.items():
        print(f"    {k:<16}: {v}")

    print("\n  Autoresearch records written to the Mouseion:")
    for rec in mouseion.query_knowledge("autoresearch")[:5]:
        print(f"   • {rec.content[:84]}")
    print()


if __name__ == "__main__":
    main()
