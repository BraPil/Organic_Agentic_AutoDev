"""
examples/distributed_demo.py

Distributed ecosystem — demonstration.

Runs a colony of independent ecosystems concurrently under asyncio. They share
one Mouseion knowledge substrate and exchange Body visions over an in-process
message bridge, while each evolves its own population, network, and Body.

Run:
    python examples/distributed_demo.py
"""

from __future__ import annotations

import asyncio
import logging

from src.core.environment import Environment
from src.core.stem_cell import StemCell
from src.distributed import AsyncEcosystem, EcosystemCoordinator, InProcessBridge
from src.mouseion.contracts import ResourceKind
from src.mouseion.substrate import Mouseion

import random

for _name in ("mouseion.substrate", "environment", "stem_cell", "body",
              "distributed.coordinator", "distributed.ecosystem"):
    logging.getLogger(_name).setLevel(logging.ERROR)


async def main(n_nodes: int = 4, ticks: int = 40, seed: int = 42) -> None:
    rng = random.Random(seed)

    print("=" * 70)
    print("  🌐  Distributed Ecosystem Demo")
    print("=" * 70)

    # One shared substrate, one bridge — the commons that spans all nodes.
    mouseion = Mouseion(initial_resources={ResourceKind.ENERGY: 6000.0})
    bridge = InProcessBridge()
    coordinator = EcosystemCoordinator(mouseion=mouseion, bridge=bridge)

    for i in range(n_nodes):
        env = Environment(mouseion=mouseion, rng=random.Random(rng.randint(0, 99999)))
        env.seed_niches(Environment.default_niche_set())
        node = AsyncEcosystem(env=env, bridge=bridge, name=f"node-{i}")
        for _ in range(8):
            node.register(StemCell(initial_energy=18.0,
                                   rng=random.Random(rng.randint(0, 99999))))
        coordinator.add_node(node)

    # Seed the shared substrate so the commons is visibly shared by every node.
    for i in range(5):
        mouseion.store_knowledge("colony_seed", f"shared seed record {i}",
                                 topic_tags=["seed", "commons"])

    print(f"\n  Colony: {n_nodes} ecosystems | shared Mouseion | bridge='{bridge.name}'")
    print(f"  Seeded {mouseion.knowledge_count()} records into the shared substrate")
    print(f"  Running {ticks} ticks concurrently…\n")

    health = await coordinator.run(ticks)

    print("  ── Colony health ──")
    print(f"    nodes               : {health['nodes']}")
    print(f"    failed              : {health['failed']}")
    print(f"    shared knowledge    : {health['shared_knowledge']} records")
    print(f"    visions shared      : {health['total_visions_shared']}")
    print(f"    visions received    : {health['total_visions_received']}")

    print("\n  ── Per-node status ──")
    for n in health["node_status"]:
        print(f"    {n['name']:<8} tick={n['tick']:3d}  agents={n['agents_alive']:2d}  "
              f"organs={n['organs']}  visions(local/recv)="
              f"{n['visions_local']}/{n['visions_received']}")
    # Every node reads the same shared substrate.
    print("\n  Each node sees the shared commons:")
    for node in coordinator.nodes:
        print(f"    {node.name:<8} reads {node.env.mouseion.knowledge_count()} shared records")

    # ----------------------------------------------------------------
    # Explicit demonstration of cross-body vision propagation via the bridge.
    # (Organic Body visions need 3+ organs; here we inject one to show the wire.)
    # ----------------------------------------------------------------
    from src.organisms.body import BodyVision

    print("\n  ── Cross-body vision propagation (bridge) ──")
    origin = coordinator.nodes[0]
    origin.body._visions.append(BodyVision("Pursue compassionate synthesis", 0.92, [], tick=ticks))
    await origin._publish_new_visions()
    print(f"    {origin.name} broadcast a vision over the bridge…")
    for node in coordinator.nodes[1:]:
        print(f"    {node.name:<8} received it → {node.received_visions} cross-body vision(s)")

    await coordinator.close()
    print("\n  All nodes shared one knowledge substrate, and one Body's vision "
          "reached every peer.\n")


if __name__ == "__main__":
    asyncio.run(main())
