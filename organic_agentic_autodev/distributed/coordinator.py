"""
src/distributed/coordinator.py

EcosystemCoordinator — orchestrates a colony of AsyncEcosystems.

The coordinator owns the shared Mouseion substrate and the MessageBridge, holds
N AsyncEcosystem nodes, runs them concurrently under asyncio, and monitors their
health. Nodes share knowledge (one Mouseion) and direction (the bridge) while
evolving independently.

Graceful degradation: if a node fails mid-run, the coordinator records it and
the surviving nodes continue. Cross-body messages to a disconnected node are
simply not delivered until it reconnects.
"""

from __future__ import annotations

import asyncio

from organic_agentic_autodev.distributed.async_environment import AsyncEcosystem
from organic_agentic_autodev.distributed.bridge import InProcessBridge, MessageBridge
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.utils.helpers import get_logger

logger = get_logger("distributed.coordinator")


class EcosystemCoordinator:
    """Runs and monitors a colony of distributed ecosystems."""

    def __init__(
        self,
        mouseion: Mouseion | None = None,
        bridge: MessageBridge | None = None,
    ) -> None:
        self.mouseion = mouseion or Mouseion()
        self.bridge = bridge or InProcessBridge()
        self.nodes: list[AsyncEcosystem] = []
        self._failures: dict[str, str] = {}

    def add_node(self, node: AsyncEcosystem) -> None:
        self.nodes.append(node)
        logger.info("Coordinator registered node '%s' (%s)", node.name, node.ecosystem_id)

    async def run(self, ticks: int, tick_delay: float = 0.0) -> dict:
        """
        Run all nodes concurrently for ``ticks`` steps.

        Returns a health summary. A node that raises is recorded as failed; the
        others still complete (return_exceptions=True).
        """
        results = await asyncio.gather(
            *[node.run(ticks, tick_delay) for node in self.nodes],
            return_exceptions=True,
        )
        for node, result in zip(self.nodes, results):
            if isinstance(result, Exception):
                self._failures[node.ecosystem_id] = repr(result)
                logger.warning("Node '%s' failed: %s", node.name, result)
        return self.health()

    def health(self) -> dict:
        """Return a colony-wide health report."""
        return {
            "nodes": len(self.nodes),
            "failed": len(self._failures),
            "shared_knowledge": self.mouseion.knowledge_count(),
            "bridge": self.bridge.name,
            "total_visions_shared": sum(len(n.body._visions) for n in self.nodes),
            "total_visions_received": sum(n.received_visions for n in self.nodes),
            "node_status": [n.snapshot() for n in self.nodes],
        }

    async def close(self) -> None:
        await self.bridge.close()
