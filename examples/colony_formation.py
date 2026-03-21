"""
examples/colony_formation.py

Watch a colony of StemCells form, differentiate, and self-organise.

This demo:
  1. Seeds 20 StemCells with varied genomes
  2. Runs 50 ticks of the environment
  3. Tracks differentiation events in real time
  4. Shows the final population breakdown by role

Run with:
    python examples/colony_formation.py
"""

import sys
import os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.genome import Genome
from src.core.stem_cell import StemCell
from src.core.environment import Environment
from src.mouseion.substrate import Mouseion
from src.mouseion.contracts import EventKind
from src.evolution.selector import Selector


def main() -> None:
    print("=" * 60)
    print("  Colony Formation Demo  (20 StemCells, 50 ticks)")
    print("=" * 60)

    rng = random.Random(42)

    # Infrastructure
    mouseion = Mouseion()
    env = Environment(mouseion=mouseion, neighbourhood_radius=20, rng=rng)
    selector = Selector(carrying_capacity=30, rng=rng)

    # Seed niches
    niches = Environment.default_niche_set()
    env.seed_niches(niches)

    # Track differentiation events
    diff_events: list[dict] = []
    mouseion.subscribe(
        EventKind.DIFFERENTIATION_COMPLETED,
        lambda e: diff_events.append({
            "tick": "?",
            "agent": e.source_agent_id,
            "role": e.payload.get("new_role"),
        }),
    )

    # Create 20 StemCells with varied random genomes
    print(f"\n[Colony] Spawning 20 StemCells...")
    for i in range(20):
        genome = Genome.random(rng=rng)
        cell = StemCell(genome=genome, initial_energy=rng.uniform(8.0, 15.0), rng=rng)
        env.register(cell)

    print(f"  Initial population: {env.agent_count()} agents")

    # Simulation loop
    print("\n[Simulation] Running...\n")
    print(f"  {'Tick':>4}  {'Alive':>5}  {'Died':>5}  {'OpenNiches':>10}  {'Knowledge':>10}")
    print("  " + "-" * 45)

    for tick in range(1, 51):
        result = env.tick()

        # Apply selection pressure every 10 ticks
        if tick % 10 == 0:
            sel_result = selector.apply(env)

        if tick % 5 == 0:
            print(f"  {tick:>4}  {result['agents_alive']:>5}  {result['agents_died']:>5}  "
                  f"{result['open_niches']:>10}  {mouseion.knowledge_count():>10}")

    # Final report
    print("\n" + "=" * 60)
    print("  FINAL COLONY STATE")
    print("=" * 60)

    agents = env.all_agents()
    role_counts: dict[str, int] = {}
    for agent in agents:
        role = agent.role.value
        role_counts[role] = role_counts.get(role, 0) + 1

    print(f"\n  Total surviving agents: {len(agents)}")
    print(f"\n  Role distribution:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"    {role:<20} {count:>3}  {bar}")

    print(f"\n  Differentiation events: {len(diff_events)}")
    for de in diff_events[:5]:
        print(f"    Agent {de['agent'][:12]}... → {de['role']}")
    if len(diff_events) > 5:
        print(f"    ... and {len(diff_events) - 5} more")

    print(f"\n  Mouseion summary:")
    summary = mouseion.summary()
    for k, v in summary.items():
        if k != "resources":
            print(f"    {k}: {v}")
    print(f"    energy_available: {summary['resources']['energy']['available']:.1f}")

    print("\n✅ Colony formation demo complete.")


if __name__ == "__main__":
    main()
