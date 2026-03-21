"""
examples/basic_stem_cell.py

Demonstrates the lifecycle of a single StemCell:
  1. Birth as a blank slate
  2. Registration in the environment
  3. Drive loop: resource-seeking → proximity scan → niche evaluation
  4. Differentiation when signals accumulate
  5. Post-differentiation specialised behaviour

Run with:
    python examples/basic_stem_cell.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.genome import Genome
from src.core.stem_cell import StemCell
from src.core.environment import Environment
from src.mouseion.substrate import Mouseion


def main() -> None:
    print("=" * 60)
    print("  Basic StemCell Lifecycle Demo")
    print("=" * 60)

    # 1. Create the shared Mouseion substrate
    mouseion = Mouseion()
    print(f"\n[Mouseion] Initialised: {mouseion.summary()}")

    # 2. Create the Environment
    env = Environment(mouseion=mouseion, neighbourhood_radius=100)

    # 3. Seed niches so the StemCell has something to differentiate toward
    niches = Environment.default_niche_set()
    env.seed_niches(niches)
    print(f"\n[Environment] Seeded {len(niches)} niches:")
    for niche in niches:
        print(f"  {niche}")

    # 4. Create a StemCell with a curious, creative genome
    genome = Genome(
        curiosity=0.9,
        creativity=0.8,
        risk_tolerance=0.6,
        cooperation=0.7,
        specialisation=0.2,  # starts undifferentiated
        compassion=0.8,
        resilience=0.6,
        persistence=0.7,
        differentiation_threshold=0.5,  # lower threshold for demo
    )
    cell = StemCell(genome=genome, initial_energy=20.0)
    env.register(cell)
    print(f"\n[Cell] Created: {cell}")
    print(f"       Genome dominant trait: {genome.dominant_trait()}")

    # 5. Run simulation ticks
    print("\n[Simulation] Running 30 ticks...\n")
    for tick in range(1, 31):
        result = env.tick()
        snapshot = cell.snapshot()

        if tick % 5 == 0 or cell.is_differentiated:
            print(f"  Tick {tick:2d}: energy={snapshot['energy']:.1f}, "
                  f"role={snapshot['role']}, "
                  f"differentiated={snapshot['differentiated']}, "
                  f"signal={snapshot['strongest_signal']}")

        if cell.is_differentiated:
            print(f"\n  🌱 DIFFERENTIATION COMPLETE at tick {tick}!")
            print(f"     Role: {cell.role.value}")
            print(f"     Energy: {cell.energy:.1f}")
            break

    # 6. Final state
    print("\n[Final State]")
    print(f"  Agent: {cell}")
    print(f"  Mouseion: {mouseion.summary()}")
    print(f"\n[Knowledge Records]")
    for record in list(mouseion.all_knowledge())[:3]:
        print(f"  [{record.record_id}] {record.content[:60]}... (conf={record.confidence:.2f})")

    print("\n✅ Demo complete.")


if __name__ == "__main__":
    main()
