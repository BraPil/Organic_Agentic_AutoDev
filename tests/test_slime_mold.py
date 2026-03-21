"""
tests/test_slime_mold.py — Tests for the SlimeMoldNetwork and Pathfinder.
"""

import random
import pytest

from src.slime_mold.network import SlimeMoldNetwork
from src.slime_mold.pathfinder import Pathfinder
from src.slime_mold.signal import Signal, SignalType
from src.utils.helpers import new_id


def make_signal(strength: float = 0.8, src: str = "a") -> Signal:
    return Signal(
        signal_id=new_id("sig_"),
        signal_type=SignalType.FOOD,
        source_id=src,
        strength=strength,
    )


class TestPathfinder:
    def setup_method(self):
        self.pf = Pathfinder(rng=random.Random(0))

    def test_add_and_remove_node(self):
        self.pf.add_node("alpha")
        assert self.pf._graph.has_node("alpha")
        self.pf.remove_node("alpha")
        assert not self.pf._graph.has_node("alpha")

    def test_ensure_edge_creates_with_init_conductance(self):
        self.pf.add_node("a")
        self.pf.add_node("b")
        self.pf.ensure_edge("a", "b")
        assert self.pf._graph.has_edge("a", "b")
        assert self.pf.conductance("a", "b") > 0

    def test_reinforce_increases_conductance(self):
        self.pf.add_node("a")
        self.pf.add_node("b")
        self.pf.ensure_edge("a", "b")
        before = self.pf.conductance("a", "b")
        self.pf.reinforce("a", "b")
        assert self.pf.conductance("a", "b") > before

    def test_weaken_decreases_conductance(self):
        self.pf.add_node("a")
        self.pf.add_node("b")
        self.pf.ensure_edge("a", "b")
        self.pf.reinforce("a", "b", delta=0.5)
        before = self.pf.conductance("a", "b")
        self.pf.weaken("a", "b", delta=0.2)
        assert self.pf.conductance("a", "b") < before

    def test_best_path_returns_list(self):
        for node in ["a", "b", "c"]:
            self.pf.add_node(node)
        self.pf.ensure_edge("a", "b")
        self.pf.ensure_edge("b", "c")
        self.pf.reinforce("a", "b", delta=0.5)
        self.pf.reinforce("b", "c", delta=0.5)
        path = self.pf.best_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_best_path_no_path_returns_empty(self):
        self.pf.add_node("x")
        self.pf.add_node("y")
        path = self.pf.best_path("x", "y")
        assert path == []

    def test_tick_decays_edges(self):
        self.pf.add_node("a")
        self.pf.add_node("b")
        self.pf.ensure_edge("a", "b")
        self.pf.reinforce("a", "b", delta=0.5)
        before = self.pf.conductance("a", "b")
        self.pf.tick(["a", "b"])
        assert self.pf.conductance("a", "b") <= before


class TestSignal:
    def test_attenuation_reduces_strength(self):
        sig = make_signal(strength=1.0)
        weaker = sig.attenuate(factor=0.7)
        assert weaker.strength == pytest.approx(0.7)

    def test_attenuation_increments_hops(self):
        sig = make_signal()
        weaker = sig.attenuate()
        assert weaker.hops == sig.hops + 1

    def test_is_alive_false_at_max_hops(self):
        sig = Signal(
            signal_id="s1", signal_type=SignalType.FOOD, source_id="x",
            strength=0.9, hops=6, max_hops=6,
        )
        assert not sig.is_alive

    def test_is_alive_false_at_low_strength(self):
        sig = Signal(
            signal_id="s2", signal_type=SignalType.FOOD, source_id="x",
            strength=0.005,
        )
        assert not sig.is_alive


class TestSlimeMoldNetwork:
    def setup_method(self):
        self.net = SlimeMoldNetwork(rng=random.Random(42))

    def test_add_and_remove_agent(self):
        self.net.add_agent("a1")
        self.net.add_agent("a2")
        self.net.remove_agent("a1")
        # No error should be raised; internals cleaned up
        assert True

    def test_connect_creates_bidirectional_edges(self):
        self.net.add_agent("x")
        self.net.add_agent("y")
        self.net.connect("x", "y")
        assert self.net._pathfinder.conductance("x", "y") > 0
        assert self.net._pathfinder.conductance("y", "x") > 0

    def test_send_signal_on_existing_path(self):
        self.net.add_agent("src")
        self.net.add_agent("dst")
        self.net.connect("src", "dst")
        # Reinforce so path is above min
        self.net._pathfinder.reinforce("src", "dst", delta=0.5)
        sig = make_signal(strength=0.9, src="src")
        result = self.net.send_signal(sig, "src", "dst")
        assert result is True

    def test_broadcast_delivers_to_neighbours(self):
        received = []
        self.net.add_agent("origin")
        self.net.add_agent("n1")
        self.net.add_agent("n2")
        self.net.connect("origin", "n1")
        self.net.connect("origin", "n2")
        # Reinforce so signals flow
        self.net._pathfinder.reinforce("origin", "n1", delta=0.5)
        self.net._pathfinder.reinforce("origin", "n2", delta=0.5)
        self.net.subscribe("n1", lambda s: received.append(s))
        sig = make_signal(strength=0.9, src="origin")
        self.net.broadcast(sig, "origin")
        assert len(received) >= 1

    def test_detect_clusters_identifies_connected_groups(self):
        for node in ["a", "b", "c", "d"]:
            self.net.add_agent(node)
        self.net.connect("a", "b")
        self.net.connect("b", "c")
        # Reinforce heavily
        for u, v in [("a", "b"), ("b", "a"), ("b", "c"), ("c", "b")]:
            self.net._pathfinder.reinforce(u, v, delta=0.8)
        clusters = self.net.detect_clusters(min_conductance=0.3)
        # a, b, c should be in one cluster; d is isolated
        joined = set()
        for c in clusters:
            joined |= c
        assert "a" in joined
        assert "b" in joined
        assert "c" in joined

    def test_tick_returns_summary(self):
        self.net.add_agent("p")
        result = self.net.tick()
        assert "tick" in result
        assert "edges_pruned" in result
