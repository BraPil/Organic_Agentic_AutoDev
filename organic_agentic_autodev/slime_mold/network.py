"""
src/slime_mold/network.py

SlimeMoldNetwork — the adaptive communication layer of the organic system.

Integrates the Pathfinder (graph conductance) with the Signal propagation
system to create a full bio-mimicking inter-agent communication substrate.

Key behaviours:
  1. Agents register as nodes when they join the ecosystem
  2. Messages (Signals) are routed along highest-conductance paths
  3. Successful delivery reinforces the path; failure weakens it
  4. Each tick, conductance decays, exploratory tendrils probe new connections
  5. Clusters of highly-connected nodes correspond to emerging Organs
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Callable

from organic_agentic_autodev.slime_mold.pathfinder import Pathfinder
from organic_agentic_autodev.slime_mold.signal import Signal, SignalType
from organic_agentic_autodev.utils.helpers import get_logger, new_id

logger = get_logger("slime_mold.network")


class SlimeMoldNetwork:
    """
    The adaptive connection topology for one ecosystem.

    Usage:
        net = SlimeMoldNetwork()
        net.add_agent("agent_a")
        net.add_agent("agent_b")
        net.connect("agent_a", "agent_b")
        net.send_signal(Signal(...), "agent_a", "agent_b")
        net.tick()
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._pathfinder = Pathfinder(rng=self._rng)
        # signal_id → Signal (in-flight signals)
        self._in_flight: dict[str, Signal] = {}
        # Delivered signal history (capped)
        self._delivered: list[dict[str, Any]] = []
        self._MAX_HISTORY = 500
        # Per-node signal accumulators (node_id → type → cumulative strength)
        self._node_accumulator: dict[str, dict[SignalType, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        # Subscribers: node_id → list of callbacks
        self._node_subscribers: dict[str, list[Callable[[Signal], None]]] = defaultdict(list)
        self._tick = 0

    # ------------------------------------------------------------------
    # Node / edge management
    # ------------------------------------------------------------------

    def add_agent(self, agent_id: str, **attrs: Any) -> None:
        self._pathfinder.add_node(agent_id, **attrs)
        logger.debug("SlimeMoldNetwork: node added %s", agent_id)

    def remove_agent(self, agent_id: str) -> None:
        self._pathfinder.remove_node(agent_id)
        self._node_accumulator.pop(agent_id, None)
        self._node_subscribers.pop(agent_id, None)

    def connect(self, src: str, dst: str) -> None:
        """Explicitly connect two nodes (bidirectional)."""
        self._pathfinder.ensure_edge(src, dst)
        self._pathfinder.ensure_edge(dst, src)

    def reinforce(self, src: str, dst: str, delta: float = 0.1) -> None:
        """Strengthen the path src→dst (successful delivery or cluster affinity)."""
        self._pathfinder.reinforce(src, dst, delta=delta)

    def subscribe(self, agent_id: str, callback: Callable[[Signal], None]) -> None:
        """Register a callback to receive signals delivered to agent_id."""
        self._node_subscribers[agent_id].append(callback)

    # ------------------------------------------------------------------
    # Signal routing
    # ------------------------------------------------------------------

    def broadcast(self, signal: Signal, origin_id: str) -> None:
        """
        Broadcast a signal from origin to all connected nodes.
        Signals propagate hop-by-hop; each hop attenuates the signal.
        """
        self._in_flight[signal.signal_id] = signal
        # Propagate to direct neighbours immediately
        for neighbour in self._pathfinder.neighbours(origin_id, min_conductance=0.05):
            weaker = signal.attenuate()
            if weaker.is_alive:
                self._deliver(weaker, neighbour, origin_id)

    def send_signal(self, signal: Signal, src: str, dst: str) -> bool:
        """
        Send a signal along the best path from src to dst.
        Returns True if a path was found, False otherwise.
        """
        path = self._pathfinder.best_path(src, dst)
        if not path or len(path) < 2:
            self._pathfinder.weaken(src, dst)
            return False

        # Propagate along path, reinforcing each hop
        current_signal = signal
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            self._pathfinder.reinforce(u, v)
            current_signal = current_signal.attenuate()
            if not current_signal.is_alive:
                break
            if i == len(path) - 2:  # final destination
                self._deliver(current_signal, v, u)
        return True

    def _deliver(self, signal: Signal, node_id: str, from_id: str) -> None:
        """Deliver a signal to a node and trigger callbacks."""
        self._node_accumulator[node_id][signal.signal_type] += signal.strength

        record = {
            "signal_id": signal.signal_id,
            "type": signal.signal_type.value,
            "to": node_id,
            "from": from_id,
            "strength": signal.strength,
            "tick": self._tick,
        }
        self._delivered.append(record)
        if len(self._delivered) > self._MAX_HISTORY:
            self._delivered.pop(0)

        for cb in self._node_subscribers.get(node_id, []):
            try:
                cb(signal)
            except Exception as exc:
                logger.error("Signal subscriber error at %s: %s", node_id, exc)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> dict:
        """
        Advance the network by one tick.
        Returns a summary of network state.
        """
        self._tick += 1
        agent_ids = list(self._pathfinder._graph.nodes())
        pruned = self._pathfinder.tick(agent_ids)
        # Decay accumulators
        for node_acc in self._node_accumulator.values():
            for stype in list(node_acc.keys()):
                node_acc[stype] *= 0.9
        return {"tick": self._tick, "edges_pruned": pruned, **self._pathfinder.summary()}

    # ------------------------------------------------------------------
    # Cluster detection (emergent Organs)
    # ------------------------------------------------------------------

    def detect_clusters(self, min_conductance: float = 0.3) -> list[set[str]]:
        """
        Identify strongly connected subgraphs — these are candidate Organs.
        Uses weak connected components on edges above a conductance threshold.
        """
        try:
            import networkx as nx
        except ImportError:
            return []

        # Build subgraph with only strong edges
        strong = nx.DiGraph()
        for u, v, d in self._pathfinder._graph.edges(data=True):
            if d.get("conductance", 0) >= min_conductance:
                strong.add_edge(u, v)

        components = list(nx.weakly_connected_components(strong))
        return [c for c in components if len(c) >= 2]

    # ------------------------------------------------------------------
    # Stats / introspection
    # ------------------------------------------------------------------

    def accumulated_signal(self, agent_id: str, signal_type: SignalType) -> float:
        return self._node_accumulator[agent_id].get(signal_type, 0.0)

    def total_signals_delivered(self) -> int:
        return len(self._delivered)

    def summary(self) -> dict:
        return {
            **self._pathfinder.summary(),
            "signals_delivered": len(self._delivered),
            "tick": self._tick,
        }
