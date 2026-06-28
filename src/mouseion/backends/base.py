"""
src/mouseion/backends/base.py

KnowledgeBackend — the shell contract for durable knowledge storage.

The Mouseion's knowledge store is the ecosystem's durable corpus (the actual
"Library of Alexandria"). This abstract base defines the seam that lets the
storage layer be swapped — in-memory, SQLite, PostgreSQL — without changing the
Mouseion's public API or any caller.

Responsibilities split (MoltBook):
  - Mouseion (shell)  : sanitisation, hashing, record construction, events
  - KnowledgeBackend  : persistence + retrieval of fully-formed records

The backend stores and returns KnowledgeRecordV0 objects verbatim. It does NOT
sanitise or construct records — that is the Mouseion's job, done once before the
record reaches the backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from src.mouseion.contracts import KnowledgeRecordV0


class KnowledgeBackend(ABC):
    """Abstract durable store for KnowledgeRecordV0 objects."""

    #: Human-readable backend name (e.g. "memory", "sqlite").
    name: str = "abstract"

    @abstractmethod
    def put(self, record: KnowledgeRecordV0) -> None:
        """Persist a fully-formed knowledge record (overwrites by record_id)."""
        raise NotImplementedError

    @abstractmethod
    def get(self, record_id: str) -> KnowledgeRecordV0 | None:
        """Return a record by id, or None if absent."""
        raise NotImplementedError

    @abstractmethod
    def query_by_tag(self, tag: str) -> list[KnowledgeRecordV0]:
        """Return all records carrying the given topic tag."""
        raise NotImplementedError

    @abstractmethod
    def all(self) -> Iterator[KnowledgeRecordV0]:
        """Iterate over all stored records."""
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored records."""
        raise NotImplementedError

    def search(self, text: str, limit: int = 10) -> list[KnowledgeRecordV0]:
        """
        Full-text search over record content.

        Default implementation is a case-insensitive substring scan; durable
        backends (SQLite/FTS5) override this with a real index. Optional — not
        every caller needs it.
        """
        needle = text.lower()
        hits = [r for r in self.all() if needle in r.content.lower()]
        return hits[:limit]

    def close(self) -> None:
        """Release any resources (no-op for in-memory backends)."""
        return None
