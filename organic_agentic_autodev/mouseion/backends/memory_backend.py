"""
src/mouseion/backends/memory_backend.py

In-memory KnowledgeBackend — the default flesh.

This preserves the exact behaviour of the original Mouseion knowledge store
(a dict keyed by record_id plus a tag → record_ids index), extracted behind the
KnowledgeBackend interface. It is the default backend, so existing code and the
full test suite run unchanged.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Iterator

from organic_agentic_autodev.mouseion.backends.base import KnowledgeBackend
from organic_agentic_autodev.mouseion.contracts import KnowledgeRecordV0


class MemoryBackend(KnowledgeBackend):
    """Thread-safe in-memory knowledge store (volatile)."""

    name = "memory"

    def __init__(self) -> None:
        self._records: dict[str, KnowledgeRecordV0] = {}
        self._tag_index: dict[str, list[str]] = defaultdict(list)
        self._lock = threading.Lock()

    def put(self, record: KnowledgeRecordV0) -> None:
        with self._lock:
            is_new = record.record_id not in self._records
            self._records[record.record_id] = record
            if is_new:
                for tag in record.topic_tags:
                    self._tag_index[tag].append(record.record_id)

    def get(self, record_id: str) -> KnowledgeRecordV0 | None:
        with self._lock:
            return self._records.get(record_id)

    def query_by_tag(self, tag: str) -> list[KnowledgeRecordV0]:
        with self._lock:
            ids = self._tag_index.get(tag, [])
            return [self._records[i] for i in ids if i in self._records]

    def all(self) -> Iterator[KnowledgeRecordV0]:
        with self._lock:
            # Materialise under lock to avoid mutation-during-iteration.
            return iter(list(self._records.values()))

    def count(self) -> int:
        with self._lock:
            return len(self._records)
