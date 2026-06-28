"""
src/distributed/bridge.py

Inter-Body message bridge — the seam that connects multiple ecosystems.

When several Environments run concurrently (each with its own Body), they
coordinate through a bridge: a Body broadcasts a SYNC vision, the bridge fans it
out to every *other* ecosystem, and each receiver re-broadcasts it into its own
slime mold network. This lets independent bodies share direction without tight
coupling.

MoltBook shell/flesh:
  - MessageBridge (shell)  — abstract async pub/sub
  - InProcessBridge (flesh) — default, single-process, zero dependencies
  - RedisBridge (flesh)     — optional, for true multi-process / multi-machine

The bridge is deliberately tiny and topic-based so a Redis (or NATS, or
ZeroMQ) implementation is a drop-in replacement.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable

from organic_agentic_autodev.utils.helpers import get_logger, new_id

logger = get_logger("distributed.bridge")

# A bridge subscriber may be sync or async.
Subscriber = Callable[[dict], Any] | Callable[[dict], Awaitable[Any]]


@dataclass
class CrossBodyMessage:
    """A message passed between ecosystems over the bridge."""
    message_id: str
    origin_body: str
    kind: str                       # e.g. "vision_sync"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class MessageBridge(ABC):
    """Abstract async pub/sub bridge between ecosystems."""

    name: str = "abstract"

    @abstractmethod
    async def publish(self, topic: str, message: CrossBodyMessage) -> None: ...

    @abstractmethod
    def subscribe(self, topic: str, callback: Subscriber) -> None: ...

    @abstractmethod
    def unsubscribe(self, topic: str, callback: Subscriber) -> None: ...

    async def close(self) -> None:
        return None


class InProcessBridge(MessageBridge):
    """Default in-process bridge — async fan-out to local subscribers."""

    name = "in_process"

    def __init__(self) -> None:
        self._subs: dict[str, list[Subscriber]] = defaultdict(list)
        self._delivered = 0

    async def publish(self, topic: str, message: CrossBodyMessage) -> None:
        payload = message.to_dict()
        for cb in list(self._subs.get(topic, [])):
            try:
                result = cb(payload)
                if asyncio.iscoroutine(result):
                    await result
                self._delivered += 1
            except Exception as exc:  # a bad subscriber must not break the bridge
                logger.warning("Bridge subscriber error on %s: %s", topic, exc)

    def subscribe(self, topic: str, callback: Subscriber) -> None:
        self._subs[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Subscriber) -> None:
        if callback in self._subs.get(topic, []):
            self._subs[topic].remove(callback)

    @property
    def delivered(self) -> int:
        return self._delivered


class RedisBridge(MessageBridge):  # pragma: no cover - optional dependency
    """
    Redis Pub/Sub bridge for true multi-process / multi-machine deployment.

    Requires ``redis`` (``pip install redis``). Lazily imported so the default
    in-process path needs no dependency.
    """

    name = "redis"

    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        import redis.asyncio as redis  # lazy import

        self._redis = redis.from_url(url)
        self._pubsub = self._redis.pubsub()
        self._tasks: list[asyncio.Task] = []
        self._json = __import__("json")

    async def publish(self, topic: str, message: CrossBodyMessage) -> None:
        await self._redis.publish(topic, self._json.dumps(message.to_dict()))

    def subscribe(self, topic: str, callback: Subscriber) -> None:
        async def _listen() -> None:
            await self._pubsub.subscribe(topic)
            async for raw in self._pubsub.listen():
                if raw.get("type") == "message":
                    payload = self._json.loads(raw["data"])
                    result = callback(payload)
                    if asyncio.iscoroutine(result):
                        await result

        self._tasks.append(asyncio.ensure_future(_listen()))

    def unsubscribe(self, topic: str, callback: Subscriber) -> None:
        # Redis unsubscribe is topic-level; cancel listeners on close().
        return None

    async def close(self) -> None:
        for t in self._tasks:
            t.cancel()
        await self._redis.aclose()
