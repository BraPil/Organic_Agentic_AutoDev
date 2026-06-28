"""
src/distributed/runner.py

Convenience builders for a distributed ecosystem colony.

``build_colony`` wires a coordinator with N AsyncEcosystem nodes that all share
one Mouseion substrate and one bridge, each seeded with its own population of
StemCells. ``run_colony`` is a one-call async entry point.
"""

from __future__ import annotations

import random

from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.core.stem_cell import StemCell
from organic_agentic_autodev.distributed.async_environment import AsyncEcosystem
from organic_agentic_autodev.distributed.bridge import InProcessBridge, MessageBridge
from organic_agentic_autodev.distributed.coordinator import EcosystemCoordinator
from organic_agentic_autodev.mouseion.contracts import ResourceKind
from organic_agentic_autodev.mouseion.substrate import Mouseion


def build_colony(
    n_nodes: int = 3,
    agents_per_node: int = 8,
    bridge: MessageBridge | None = None,
    initial_energy: float = 4000.0,
    seed: int = 42,
) -> EcosystemCoordinator:
    """
    Build a coordinator with ``n_nodes`` ecosystems sharing one Mouseion.

    Each node has an independent Environment, network, Body and population, but
    they all read/write the same knowledge substrate and exchange visions over a
    shared bridge.
    """
    rng = random.Random(seed)
    mouseion = Mouseion(initial_resources={ResourceKind.ENERGY: initial_energy})
    coordinator = EcosystemCoordinator(
        mouseion=mouseion,
        bridge=bridge or InProcessBridge(),
    )

    for i in range(n_nodes):
        env = Environment(mouseion=mouseion, rng=random.Random(rng.randint(0, 99999)))
        env.seed_niches(Environment.default_niche_set())
        node = AsyncEcosystem(env=env, bridge=coordinator.bridge, name=f"node-{i}")
        for _ in range(agents_per_node):
            node.register(StemCell(initial_energy=15.0,
                                   rng=random.Random(rng.randint(0, 99999))))
        coordinator.add_node(node)

    return coordinator


async def run_colony(
    n_nodes: int = 3,
    agents_per_node: int = 8,
    ticks: int = 30,
    seed: int = 42,
) -> dict:
    """Build and run a colony, returning the final health report."""
    coordinator = build_colony(n_nodes=n_nodes, agents_per_node=agents_per_node, seed=seed)
    report = await coordinator.run(ticks)
    await coordinator.close()
    return report
