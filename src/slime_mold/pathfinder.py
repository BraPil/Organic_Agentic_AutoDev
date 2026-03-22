"""
src/slime_mold/pathfinder.py

Path reinforcement and discovery for the slime mold network.

Models Physarum's tube-reinforcement rule:
  - Tubes carrying more flux grow thicker (lower resistance)
  - Tubes carrying little flux thin and eventually disappear
  - New exploratory tendrils are sent out randomly at low cost

The pathfinder operates on a NetworkX directed graph where:
  - Nodes are agent IDs
  - Edge weight = conductance (high → fast flow → reinforced)
  - Edges below a minimum conductance threshold are pruned
"""

from __future__ import annotations

import random
from typing import Any

try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False

from src.utils.helpers import clamp, get_logger

logger = get_logger("slime_mold.pathfinder")

# Conductance bounds
MIN_CONDUCTANCE = 0.01
MAX_CONDUCTANCE = 1.0
# Reinforcement per successful signal delivery
REINFORCE_DELTA = 0.1
# Decay per tick on all edges
DECAY_RATE = 0.02
# Probability of exploring a new random edge each tick
EXPLORE_PROB = 0.05
# Initial conductance for new exploratory edges
INIT_CONDUCTANCE = 0.05


class Pathfinder:
    """
    Manages the slime mold connection graph for one ecosystem.

    All conductance updates are idempotent and reversible — no
    permanent state changes that can't be overridden by usage signals.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        if not HAS_NX:
            raise ImportError("networkx is required for Pathfinder. pip install networkx")
        self._graph: Any = nx.DiGraph()
        self.rng = rng or random.Random()
        self._tick = 0

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(self, agent_id: str, **attrs: Any) -> None:
        self._graph.add_node(agent_id, **attrs)

    def remove_node(self, agent_id: str) -> None:
        if self._graph.has_node(agent_id):
            self._graph.remove_node(agent_id)

    # ------------------------------------------------------------------
    # Edge management
    # ------------------------------------------------------------------

    def ensure_edge(self, src: str, dst: str) -> None:
        """Create an edge if it doesn't exist, with initial conductance."""
        if not self._graph.has_edge(src, dst):
            self._graph.add_edge(src, dst, conductance=INIT_CONDUCTANCE, flux=0.0)

    def reinforce(self, src: str, dst: str, delta: float = REINFORCE_DELTA) -> None:
        """Strengthen the path src→dst (successful message delivery)."""
        self.ensure_edge(src, dst)
        old = self._graph[src][dst]["conductance"]
        self._graph[src][dst]["conductance"] = clamp(old + delta, MIN_CONDUCTANCE, MAX_CONDUCTANCE)
        self._graph[src][dst]["flux"] += 1

    def weaken(self, src: str, dst: str, delta: float = REINFORCE_DELTA) -> None:
        """Weaken path src→dst (failed or inefficient delivery)."""
        if not self._graph.has_edge(src, dst):
            return
        old = self._graph[src][dst]["conductance"]
        self._graph[src][dst]["conductance"] = max(MIN_CONDUCTANCE, old - delta)

    # ------------------------------------------------------------------
    # Tick: decay + prune + explore
    # ------------------------------------------------------------------

    def tick(self, agent_ids: list[str]) -> int:
        """
        Advance one simulation step.
        Returns number of edges pruned.
        """
        self._tick += 1
        pruned = 0

        # 1. Decay all edges
        edges_to_remove: list[tuple[str, str]] = []
        for u, v, data in list(self._graph.edges(data=True)):
            data["conductance"] = max(MIN_CONDUCTANCE, data["conductance"] - DECAY_RATE)
            if data["conductance"] <= MIN_CONDUCTANCE * 1.1 and data.get("flux", 0) == 0:
                edges_to_remove.append((u, v))

        # 2. Prune dead edges
        for u, v in edges_to_remove:
            self._graph.remove_edge(u, v)
            pruned += 1

        # 3. Exploratory tendrils — randomly connect nearby agents
        if len(agent_ids) >= 2 and self.rng.random() < EXPLORE_PROB:
            src, dst = self.rng.sample(agent_ids, 2)
            if src != dst:
                self.ensure_edge(src, dst)

        # 4. Reset flux counters
        for _, _, data in self._graph.edges(data=True):
            data["flux"] = 0

        return pruned

    # ------------------------------------------------------------------
    # Path queries
    # ------------------------------------------------------------------

    def best_path(self, src: str, dst: str) -> list[str]:
        """
        Find the highest-conductance path from src to dst.
        Uses NetworkX shortest path with inverted conductance as cost.
        """
        if not (self._graph.has_node(src) and self._graph.has_node(dst)):
            return []
        try:
            path = nx.shortest_path(
                self._graph, src, dst,
                weight=lambda u, v, d: 1.0 / max(d.get("conductance", 0.01), 0.001),
            )
            return list(path)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def neighbours(self, agent_id: str, min_conductance: float = 0.0) -> list[str]:
        """Return outgoing neighbours above a conductance threshold."""
        if not self._graph.has_node(agent_id):
            return []
        return [
            v for _, v, d in self._graph.out_edges(agent_id, data=True)
            if d.get("conductance", 0) >= min_conductance
        ]

    def conductance(self, src: str, dst: str) -> float:
        if self._graph.has_edge(src, dst):
            return self._graph[src][dst].get("conductance", 0.0)
        return 0.0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "tick": self._tick,
            "avg_conductance": (
                sum(d.get("conductance", 0) for _, _, d in self._graph.edges(data=True))
                / max(self._graph.number_of_edges(), 1)
            ),
        }
