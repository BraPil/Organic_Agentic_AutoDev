"""
src/distributed/async_environment.py

AsyncEcosystem — one ecosystem instance that runs cooperatively under asyncio
and coordinates with peers through a MessageBridge.

Multiple AsyncEcosystems can:
  - share a single Mouseion substrate (knowledge written by one is visible to
    all — the commons spans ecosystems), and
  - exchange Body visions over the bridge (one Body's SYNC vision is
    re-broadcast into every other ecosystem's slime mold network).

Each ecosystem owns its own Environment, SlimeMoldNetwork, Body, and agents, so
they evolve independently while sharing knowledge and high-level direction.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.distributed.bridge import CrossBodyMessage, MessageBridge
from src.organisms.body import Body
from src.slime_mold.network import SlimeMoldNetwork
from src.slime_mold.signal import Signal, SignalType
from src.utils.helpers import get_logger, new_id

if TYPE_CHECKING:
    from src.core.environment import Environment
    from src.core.stem_cell import StemCell

logger = get_logger("distributed.ecosystem")

VISION_TOPIC = "vision_sync"


class AsyncEcosystem:
    """An asyncio-driven ecosystem node in a distributed colony."""

    def __init__(
        self,
        env: "Environment",
        bridge: MessageBridge,
        name: str = "node",
        network: SlimeMoldNetwork | None = None,
        body: Body | None = None,
    ) -> None:
        self.ecosystem_id = new_id("eco_")
        self.name = name
        self.env = env
        self.bridge = bridge
        self.network = network or SlimeMoldNetwork()
        self.body = body or Body(f"{name}-body")
        self.body.attach_to_network(self.network)

        self.tick = 0
        self._last_vision_count = 0
        self.received_visions = 0
        self._running = False

        # Listen for visions from *other* ecosystems.
        self.bridge.subscribe(VISION_TOPIC, self._on_cross_body_message)

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register(self, agent: "StemCell") -> None:
        self.env.register(agent)

    # ------------------------------------------------------------------
    # Bridge handlers
    # ------------------------------------------------------------------

    def _on_cross_body_message(self, payload: dict) -> None:
        """Receive a peer's vision and re-broadcast it into the local network."""
        if payload.get("origin_body") == self.body.body_id:
            return  # ignore our own echo
        self.received_visions += 1
        self.network.broadcast(Signal(
            signal_id=new_id("sig_"),
            signal_type=SignalType.SYNC,
            source_id=self.body.body_id,
            strength=0.8,
            payload={"cross_body": True,
                     "origin": payload.get("origin_body"),
                     **payload.get("payload", {})},
        ), self.body.body_id)

    async def _publish_new_visions(self) -> None:
        """If the Body produced a new vision this tick, share it on the bridge."""
        count = len(self.body._visions)
        if count > self._last_vision_count:
            self._last_vision_count = count
            latest = self.body._visions[-1]
            await self.bridge.publish(VISION_TOPIC, CrossBodyMessage(
                message_id=new_id("msg_"),
                origin_body=self.body.body_id,
                kind="vision_sync",
                payload={"vision_id": latest.vision_id,
                         "confidence": latest.confidence,
                         "ecosystem": self.name},
            ))

    # ------------------------------------------------------------------
    # Stepping
    # ------------------------------------------------------------------

    async def step_once(self) -> None:
        """Advance this ecosystem one tick (cooperatively yields)."""
        self.tick += 1
        self.env.tick()
        self.network.tick()
        self.body.step(self.env)
        await self._publish_new_visions()
        await asyncio.sleep(0)  # yield to peers

    async def run(self, ticks: int, tick_delay: float = 0.0) -> None:
        """Run this ecosystem for ``ticks`` steps."""
        self._running = True
        try:
            for _ in range(ticks):
                if not self._running:
                    break
                await self.step_once()
                if tick_delay:
                    await asyncio.sleep(tick_delay)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False

    def disconnect(self) -> None:
        """Detach from the bridge (simulates a node going offline)."""
        self.bridge.unsubscribe(VISION_TOPIC, self._on_cross_body_message)

    def reconnect(self) -> None:
        """Re-attach to the bridge after a disconnect."""
        self.bridge.subscribe(VISION_TOPIC, self._on_cross_body_message)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "ecosystem_id": self.ecosystem_id,
            "name": self.name,
            "tick": self.tick,
            "agents_alive": self.env.agent_count(),
            "organs": self.body.organ_count,
            "visions_local": len(self.body._visions),
            "visions_received": self.received_visions,
            "running": self._running,
        }
