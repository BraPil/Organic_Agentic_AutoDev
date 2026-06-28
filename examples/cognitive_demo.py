"""
examples/cognitive_demo.py

LLM-backed agent cognition — demonstration.

Shows CognitiveCells reasoning their way to knowledge contributions. Runs fully
offline by default (deterministic MockProvider); plug in a real model simply by
exporting an API key:

    # Offline (deterministic mock) — no key needed
    python examples/cognitive_demo.py

    # Live (real Anthropic Claude)
    ANTHROPIC_API_KEY=sk-... python examples/cognitive_demo.py

The provider is auto-selected: Anthropic if ANTHROPIC_API_KEY is set, else
OpenAI if OPENAI_API_KEY is set, else the offline MockProvider. The simulation
mechanics are identical either way — that is the whole point of the shell/flesh
separation.
"""

from __future__ import annotations

import logging
import random

logging.basicConfig(level=logging.WARNING)

from src.cognition import CognitiveCell, build_system_prompt, get_provider
from src.core.environment import Environment
from src.domain.exmorbus import create_medical_genome, create_medical_niches, seed_mouseion
from src.mouseion.contracts import AgentRole, ResourceKind
from src.mouseion.substrate import Mouseion


def main(n_ticks: int = 20, seed: int = 42) -> None:
    rng = random.Random(seed)

    print("=" * 70)
    print("  🧠  LLM-Backed Agent Cognition Demo")
    print("=" * 70)

    provider = get_provider()
    print(f"\n  Cognition provider: {provider.name} "
          f"({'LIVE' if provider.is_live else 'offline mock'})")
    if not provider.is_live:
        print("  (set ANTHROPIC_API_KEY to use real Claude cognition)")

    # Substrate seeded with oncology knowledge so agents have real context.
    mouseion = Mouseion(initial_resources={ResourceKind.ENERGY: 2000.0})
    env = Environment(mouseion=mouseion, neighbourhood_radius=20, rng=rng)
    seed_mouseion(mouseion)
    env.seed_niches(create_medical_niches())
    print(f"  Seeded {mouseion.knowledge_count()} knowledge records\n")

    # A small tumour-board of cognitive specialists.
    roles = [
        AgentRole.ONCOLOGIST, AgentRole.GENETICIST,
        AgentRole.PATHOLOGIST, AgentRole.RADIOLOGIST,
    ]
    cells: list[CognitiveCell] = []
    for i, role in enumerate(roles):
        genome = create_medical_genome(role, rng=rng)
        cell = CognitiveCell(
            role=role,
            provider=provider,
            cognition_probability=1.0,
            genome=genome,
            initial_energy=40.0,
            rng=random.Random(rng.randint(0, 99999)),
        )
        env.register(cell)
        cells.append(cell)

    # Show one agent's genome-derived system prompt — the genome→prompt bridge.
    print("  ── Example genome-derived system prompt (Oncologist) ──")
    print("  " + build_system_prompt(cells[0].genome, cells[0].role).replace("\n", "\n  "))
    print()

    print("  ── Running cognition ──")
    baseline = mouseion.knowledge_count()
    for tick in range(1, n_ticks + 1):
        env.tick()
        if tick % 5 == 0:
            produced = mouseion.knowledge_count() - baseline
            calls = sum(c.cognition_count for c in cells)
            print(f"  Tick {tick:3d} | cognition calls: {calls:3d} | "
                  f"agent-produced records: {produced:3d}")

    print("\n  ── Results ──")
    for cell in cells:
        print(f"  {cell.role.value:<16} cognition_calls={cell.cognition_count:3d}  "
              f"energy={cell.energy:6.1f}  spec={cell.specialisation_score:.2f}")

    print(f"\n  Total knowledge records: {mouseion.knowledge_count()} "
          f"(seeded: {baseline}, agent-produced: {mouseion.knowledge_count() - baseline})")
    print("\n  Sample agent-produced records:")
    agent_records = [r for r in mouseion.all_knowledge()
                     if r.author_id.startswith("cell_")][:3]
    for rec in agent_records:
        print(f"   • [{rec.confidence:.2f}] {rec.content[:90]}")
    print()


if __name__ == "__main__":
    main()
