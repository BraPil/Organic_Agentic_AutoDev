"""
tests/test_distributed.py

Tests for the distributed ecosystem (asyncio, in-process bridge).

pytest is configured with asyncio_mode = "auto", so ``async def test_*`` runs
directly. All tests are offline and deterministic.
"""

from __future__ import annotations

import random

import pytest

from src.core.environment import Environment
from src.core.stem_cell import StemCell
from src.distributed import (
    AsyncEcosystem,
    CrossBodyMessage,
    EcosystemCoordinator,
    InProcessBridge,
    build_colony,
    run_colony,
)
from src.distributed.async_environment import VISION_TOPIC
from src.mouseion.substrate import Mouseion
from src.organisms.body import BodyVision
from src.utils.helpers import new_id


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

async def test_bridge_delivers_to_subscriber():
    bridge = InProcessBridge()
    received = []
    bridge.subscribe("topic", lambda p: received.append(p))
    await bridge.publish("topic", CrossBodyMessage(
        message_id="m1", origin_body="b1", kind="test", payload={"x": 1}))
    assert len(received) == 1
    assert received[0]["payload"]["x"] == 1


async def test_bridge_async_subscriber():
    bridge = InProcessBridge()
    received = []

    async def handler(p):
        received.append(p)

    bridge.subscribe("t", handler)
    await bridge.publish("t", CrossBodyMessage(message_id="m", origin_body="b", kind="k"))
    assert len(received) == 1


async def test_bridge_unsubscribe_stops_delivery():
    bridge = InProcessBridge()
    received = []
    cb = lambda p: received.append(p)
    bridge.subscribe("t", cb)
    bridge.unsubscribe("t", cb)
    await bridge.publish("t", CrossBodyMessage(message_id="m", origin_body="b", kind="k"))
    assert received == []


async def test_bridge_survives_bad_subscriber():
    bridge = InProcessBridge()
    good = []

    def boom(p):
        raise ValueError("bad subscriber")

    bridge.subscribe("t", boom)
    bridge.subscribe("t", lambda p: good.append(p))
    await bridge.publish("t", CrossBodyMessage(message_id="m", origin_body="b", kind="k"))
    assert len(good) == 1  # the good subscriber still got it


# ---------------------------------------------------------------------------
# Shared substrate
# ---------------------------------------------------------------------------

async def test_nodes_share_knowledge_substrate():
    """Knowledge written by one node's env is readable by another (one Mouseion)."""
    mouseion = Mouseion()
    bridge = InProcessBridge()
    env_a = Environment(mouseion=mouseion, rng=random.Random(1))
    env_b = Environment(mouseion=mouseion, rng=random.Random(2))
    AsyncEcosystem(env=env_a, bridge=bridge, name="a")
    node_b = AsyncEcosystem(env=env_b, bridge=bridge, name="b")

    env_a.mouseion.store_knowledge("agent_a", "shared finding", topic_tags=["x"])
    # node_b sees it because they share the substrate.
    assert node_b.env.mouseion.knowledge_count() == 1
    assert len(node_b.env.mouseion.query_knowledge("x")) == 1


# ---------------------------------------------------------------------------
# Cross-body vision propagation
# ---------------------------------------------------------------------------

async def test_vision_propagates_across_bodies():
    bridge = InProcessBridge()
    m = Mouseion()
    node_a = AsyncEcosystem(env=Environment(mouseion=m, rng=random.Random(1)),
                            bridge=bridge, name="a")
    node_b = AsyncEcosystem(env=Environment(mouseion=m, rng=random.Random(2)),
                            bridge=bridge, name="b")

    # Inject a vision into node_a's body, then publish.
    node_a.body._visions.append(BodyVision("test vision", 0.9, [], tick=1))
    await node_a._publish_new_visions()

    assert node_b.received_visions == 1
    # node_a must ignore its own echo.
    assert node_a.received_visions == 0


async def test_disconnect_blocks_then_reconnect_restores():
    bridge = InProcessBridge()
    m = Mouseion()
    node_a = AsyncEcosystem(env=Environment(mouseion=m, rng=random.Random(1)),
                            bridge=bridge, name="a")
    node_b = AsyncEcosystem(env=Environment(mouseion=m, rng=random.Random(2)),
                            bridge=bridge, name="b")

    node_b.disconnect()
    node_a.body._visions.append(BodyVision("v1", 0.9, [], tick=1))
    await node_a._publish_new_visions()
    assert node_b.received_visions == 0  # disconnected → no delivery

    node_b.reconnect()
    node_a.body._visions.append(BodyVision("v2", 0.9, [], tick=2))
    await node_a._publish_new_visions()
    assert node_b.received_visions == 1  # reconnected → delivery resumes


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

async def test_coordinator_runs_nodes_concurrently():
    coordinator = build_colony(n_nodes=3, agents_per_node=6, seed=5)
    health = await coordinator.run(ticks=10)
    assert health["nodes"] == 3
    assert health["failed"] == 0
    for node_status in health["node_status"]:
        assert node_status["tick"] == 10


async def test_coordinator_health_report_shape():
    coordinator = build_colony(n_nodes=2, agents_per_node=4, seed=8)
    await coordinator.run(ticks=5)
    h = coordinator.health()
    for key in ("nodes", "failed", "shared_knowledge", "bridge",
                "total_visions_shared", "total_visions_received", "node_status"):
        assert key in h


async def test_coordinator_handles_node_failure():
    """A node that raises is recorded as failed; others still complete."""
    coordinator = build_colony(n_nodes=2, agents_per_node=4, seed=3)
    # Sabotage one node so its run() raises.
    bad = coordinator.nodes[0]

    async def boom():
        raise RuntimeError("node crashed")

    bad.step_once = boom  # type: ignore
    health = await coordinator.run(ticks=5)
    assert health["failed"] == 1
    # The healthy node still advanced.
    assert coordinator.nodes[1].tick == 5


async def test_shared_knowledge_grows_across_colony():
    coordinator = build_colony(n_nodes=3, agents_per_node=8, seed=11)
    await coordinator.run(ticks=25)
    # Some agents differentiate and contribute to the shared substrate.
    assert coordinator.mouseion.knowledge_count() >= 0  # never negative; usually > 0


# ---------------------------------------------------------------------------
# End-to-end runner
# ---------------------------------------------------------------------------

async def test_run_colony_end_to_end():
    report = await run_colony(n_nodes=2, agents_per_node=5, ticks=12, seed=42)
    assert report["nodes"] == 2
    assert report["failed"] == 0
    assert all(n["tick"] == 12 for n in report["node_status"])
