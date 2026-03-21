"""
src/mouseion/substrate.py

The Mouseion — shared in-memory knowledge substrate for the ecosystem.

Named after the ancient Library of Alexandria: a repository of knowledge
designed to outlast any individual contributor and serve the collective.

Design contract (MoltBook shell / flesh pattern):
  SHELL (this file)  — stable API, versioned records, provenance tracking
  FLESH (future)     — swap SQLite → PostgreSQL, FAISS → Qdrant, etc.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Callable, Iterator

from src.mouseion.contracts import (
    EventEnvelopeV0,
    EventKind,
    KnowledgeRecordV0,
    NicheAdvertisementV0,
    ResourceKind,
)
from src.utils.helpers import content_hash, get_logger, new_id, now_ms, sanitize_text

logger = get_logger("mouseion.substrate")


class ResourcePool:
    """
    A named, thread-safe pool of a specific resource kind.
    Agents draw from and contribute to pools; the pool enforces conservation.
    """

    def __init__(self, kind: ResourceKind, initial: float = 100.0) -> None:
        self.kind = kind
        self._amount = initial
        self._total_drawn = 0.0
        self._total_deposited = 0.0
        self._lock = threading.Lock()

    @property
    def amount(self) -> float:
        return self._amount

    def draw(self, amount: float, agent_id: str) -> float:
        """Draw up to *amount* from the pool; returns what was actually granted."""
        with self._lock:
            granted = min(amount, self._amount)
            self._amount -= granted
            self._total_drawn += granted
        if granted < amount:
            logger.warning(
                "ResourcePool %s: agent %s requested %.2f, granted %.2f",
                self.kind.value, agent_id, amount, granted,
            )
        return granted

    def deposit(self, amount: float, agent_id: str) -> None:
        """Return or contribute *amount* to the pool."""
        with self._lock:
            self._amount += amount
            self._total_deposited += amount

    def stats(self) -> dict[str, float]:
        return {
            "available": self._amount,
            "total_drawn": self._total_drawn,
            "total_deposited": self._total_deposited,
        }


class Mouseion:
    """
    Singleton-ish shared substrate for one ecosystem instance.
    Provides:
      - Resource pools (energy, compute, data, attention, knowledge, trust)
      - Niche registry (open functional roles)
      - Knowledge store (durable records with provenance)
      - Event bus (lightweight pub/sub for cross-agent signals)
    """

    def __init__(self, initial_resources: dict[ResourceKind, float] | None = None) -> None:
        defaults = {
            ResourceKind.ENERGY: 1000.0,
            ResourceKind.COMPUTE: 500.0,
            ResourceKind.DATA: 800.0,
            ResourceKind.ATTENTION: 200.0,
            ResourceKind.KNOWLEDGE: 300.0,
            ResourceKind.TRUST: 100.0,
        }
        overrides = initial_resources or {}
        self._pools: dict[ResourceKind, ResourcePool] = {
            k: ResourcePool(k, overrides.get(k, v)) for k, v in defaults.items()
        }

        # Niche registry: niche_id → advertisement
        self._niches: dict[str, NicheAdvertisementV0] = {}
        self._niche_lock = threading.Lock()

        # Knowledge store: record_id → record
        self._knowledge: dict[str, KnowledgeRecordV0] = {}
        self._knowledge_index: dict[str, list[str]] = defaultdict(list)  # tag → record_ids
        self._knowledge_lock = threading.Lock()

        # Event bus: kind → list of subscriber callbacks
        self._subscribers: dict[EventKind, list[Callable[[EventEnvelopeV0], None]]] = defaultdict(list)
        self._event_history: list[EventEnvelopeV0] = []
        self._event_lock = threading.Lock()

        logger.info("Mouseion substrate initialised with %d resource pools", len(self._pools))

    # ------------------------------------------------------------------
    # Resource API
    # ------------------------------------------------------------------

    def draw_resource(self, kind: ResourceKind, amount: float, agent_id: str) -> float:
        return self._pools[kind].draw(amount, agent_id)

    def deposit_resource(self, kind: ResourceKind, amount: float, agent_id: str) -> None:
        self._pools[kind].deposit(amount, agent_id)

    def resource_level(self, kind: ResourceKind) -> float:
        return self._pools[kind].amount

    def resource_summary(self) -> dict[str, dict[str, float]]:
        return {k.value: v.stats() for k, v in self._pools.items()}

    # ------------------------------------------------------------------
    # Niche registry API
    # ------------------------------------------------------------------

    def post_niche(self, advert: NicheAdvertisementV0) -> None:
        with self._niche_lock:
            self._niches[advert.niche_id] = advert
        self._emit(EventEnvelopeV0(
            event_id=new_id("evt_"),
            kind=EventKind.NICHE_OPENED,
            source_agent_id=advert.posted_by,
            payload={"niche_id": advert.niche_id, "description": advert.description},
        ))
        logger.info("Niche posted: %s — %s", advert.niche_id, advert.description[:60])

    def fill_niche(self, niche_id: str, agent_id: str) -> bool:
        with self._niche_lock:
            niche = self._niches.get(niche_id)
            if niche is None or niche.filled_by is not None:
                return False
            self._niches[niche_id] = niche.model_copy(
                update={"filled_by": agent_id}
            )
        self._emit(EventEnvelopeV0(
            event_id=new_id("evt_"),
            kind=EventKind.NICHE_FILLED,
            source_agent_id=agent_id,
            payload={"niche_id": niche_id},
        ))
        logger.info("Niche %s filled by agent %s", niche_id, agent_id)
        return True

    def open_niches(self) -> list[NicheAdvertisementV0]:
        with self._niche_lock:
            return [n for n in self._niches.values() if n.filled_by is None]

    def all_niches(self) -> list[NicheAdvertisementV0]:
        with self._niche_lock:
            return list(self._niches.values())

    # ------------------------------------------------------------------
    # Knowledge store API
    # ------------------------------------------------------------------

    def store_knowledge(self, author_id: str, content: str,
                        topic_tags: list[str] | None = None,
                        confidence: float = 0.5,
                        provenance_refs: list[str] | None = None) -> KnowledgeRecordV0:
        safe_content = sanitize_text(content)
        chash = content_hash(safe_content)
        record = KnowledgeRecordV0(
            record_id=new_id("kr_"),
            author_id=author_id,
            content=safe_content,
            content_hash=chash,
            topic_tags=topic_tags or [],
            confidence=confidence,
            provenance_refs=provenance_refs or [],
        )
        with self._knowledge_lock:
            self._knowledge[record.record_id] = record
            for tag in record.topic_tags:
                self._knowledge_index[tag].append(record.record_id)

        self._emit(EventEnvelopeV0(
            event_id=new_id("evt_"),
            kind=EventKind.KNOWLEDGE_STORED,
            source_agent_id=author_id,
            payload={"record_id": record.record_id, "tags": topic_tags or []},
        ))
        return record

    def query_knowledge(self, tag: str) -> list[KnowledgeRecordV0]:
        with self._knowledge_lock:
            ids = self._knowledge_index.get(tag, [])
            return [self._knowledge[i] for i in ids if i in self._knowledge]

    def get_knowledge(self, record_id: str) -> KnowledgeRecordV0 | None:
        with self._knowledge_lock:
            return self._knowledge.get(record_id)

    def all_knowledge(self) -> Iterator[KnowledgeRecordV0]:
        with self._knowledge_lock:
            yield from self._knowledge.values()

    def knowledge_count(self) -> int:
        with self._knowledge_lock:
            return len(self._knowledge)

    # ------------------------------------------------------------------
    # Event bus API
    # ------------------------------------------------------------------

    def subscribe(self, kind: EventKind, callback: Callable[[EventEnvelopeV0], None]) -> None:
        self._subscribers[kind].append(callback)

    def _emit(self, event: EventEnvelopeV0) -> None:
        with self._event_lock:
            self._event_history.append(event)
        for cb in self._subscribers.get(event.kind, []):
            try:
                cb(event)
            except Exception as exc:
                logger.error("Event subscriber error for %s: %s", event.kind, exc)

    def emit(self, event: EventEnvelopeV0) -> None:
        """Public emit — for agents to broadcast events."""
        self._emit(event)

    def event_history(self, kind: EventKind | None = None) -> list[EventEnvelopeV0]:
        with self._event_lock:
            if kind is None:
                return list(self._event_history)
            return [e for e in self._event_history if e.kind == kind]

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        return {
            "resources": self.resource_summary(),
            "open_niches": len(self.open_niches()),
            "total_niches": len(self._niches),
            "knowledge_records": self.knowledge_count(),
            "events_emitted": len(self._event_history),
        }
