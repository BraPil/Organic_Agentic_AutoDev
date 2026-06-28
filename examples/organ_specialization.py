"""
examples/organ_specialization.py

Demonstrates the full Cell → Organ → Body emergence.

This demo:
  1. Creates a set of pre-differentiated Cells with specific roles
  2. Connects them via the SlimeMoldNetwork
  3. Clusters compatible cells into Organs
  4. Assembles Organs under a Body
  5. Runs the Body's vision synthesis cycle

Run with:
    python examples/organ_specialization.py
"""

import sys
import os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from organic_agentic_autodev.core.genome import Genome
from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.mouseion.contracts import AgentRole
from organic_agentic_autodev.organisms.cell import Cell
from organic_agentic_autodev.organisms.organ import Organ
from organic_agentic_autodev.organisms.body import Body
from organic_agentic_autodev.slime_mold.network import SlimeMoldNetwork
from organic_agentic_autodev.slime_mold.signal import Signal, SignalType
from organic_agentic_autodev.utils.helpers import new_id


def main() -> None:
    print("=" * 60)
    print("  Organ Specialisation & Body Emergence Demo")
    print("=" * 60)

    rng = random.Random(7)

    # Infrastructure
    mouseion = Mouseion()
    env = Environment(mouseion=mouseion, neighbourhood_radius=50, rng=rng)
    network = SlimeMoldNetwork(rng=rng)

    # Seed niches so the environment has context
    niches = Environment.default_niche_set()
    env.seed_niches(niches)

    # --- Create differentiated Cells ---
    print("\n[Cells] Creating differentiated specialist cells...")
    all_cells: list[Cell] = []

    role_plan = [
        (AgentRole.RESEARCHER, 3),
        (AgentRole.CODER, 3),
        (AgentRole.CRITIC, 2),
        (AgentRole.SYNTHESIZER, 2),
        (AgentRole.CONNECTOR, 2),
        (AgentRole.GUARDIAN, 1),
    ]

    for role, count in role_plan:
        for _ in range(count):
            genome = Genome.random(rng=rng)
            cell = Cell(role=role, genome=genome, initial_energy=12.0, rng=rng)
            cell.attach_to_network(network)
            env.register(cell)
            all_cells.append(cell)
            print(f"  Created {role.value} cell: {cell.agent_id[:12]}...")

    print(f"\n  Total cells: {len(all_cells)}")

    # --- Run a few ticks to let the slime mold network form ---
    print("\n[Slime Mold] Running 10 ticks to establish connections...")
    for tick in range(10):
        env.tick()
        net_stats = network.tick()

    print(f"  Network state: {network.summary()}")
    clusters = network.detect_clusters(min_conductance=0.1)
    print(f"  Detected {len(clusters)} emergent clusters")

    # --- Form Organs from cell clusters ---
    print("\n[Organs] Forming organs from aligned cell clusters...")
    body = Body(name="PrimordialBody")
    body.attach_to_network(network)

    # Group cells by role to form organs
    cells_by_role: dict[AgentRole, list[Cell]] = {}
    for cell in all_cells:
        if cell.role not in cells_by_role:
            cells_by_role[cell.role] = []
        cells_by_role[cell.role].append(cell)

    organs: list[Organ] = []
    for role, cells in cells_by_role.items():
        if len(cells) >= 2:
            organ = Organ(founding_cells=cells)
            organs.append(organ)
            body.register_organ(organ)
            print(f"  Formed {role.value} organ: {organ.organ_id[:12]}... ({len(cells)} cells)")

    print(f"\n  Body state: {body}")
    print(f"  Fully functional: {body.is_fully_functional}")

    # --- Run full system ticks ---
    print("\n[Body] Running 30 ticks of full system...")
    print(f"\n  {'Tick':>4}  {'Organs':>6}  {'Knowledge':>10}  {'Networks':>10}")
    print("  " + "-" * 40)

    for tick in range(1, 31):
        env.tick()
        network.tick()
        body_report = body.step(env)

        if tick % 5 == 0:
            print(f"  {tick:>4}  {body_report['organs']:>6}  "
                  f"{mouseion.knowledge_count():>10}  "
                  f"{network.summary()['edges']:>10}")

    # --- Final report ---
    print("\n" + "=" * 60)
    print("  FINAL BODY STATE")
    print("=" * 60)

    body_snap = body.snapshot()
    print(f"\n  Body: {body.name} ({body.body_id[:12]}...)")
    print(f"  Fully functional: {body_snap['fully_functional']}")
    print(f"  Visions generated: {body_snap['visions_count']}")
    print(f"  Age: {body_snap['age_ticks']} ticks")

    if body_snap['latest_vision']:
        print(f"\n  Latest vision:")
        print(f"    {body_snap['latest_vision']}")

    print(f"\n  Organs:")
    for organ_snap in body_snap['organs']:
        print(f"    [{organ_snap['organ_id'][:10]}...] {organ_snap['dominant_role']}: "
              f"{organ_snap['size']} cells, "
              f"spec={organ_snap['mean_specialisation']:.2f}, "
              f"records={organ_snap['knowledge_records_produced']}")

    print(f"\n  Mouseion: {mouseion.summary()}")
    print(f"  Network: {network.summary()}")

    print("\n✅ Organ specialisation demo complete.")


if __name__ == "__main__":
    main()
