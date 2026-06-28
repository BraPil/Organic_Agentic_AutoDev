"""
src/mouseion/backends/sqlite_backend.py

SQLite KnowledgeBackend — durable flesh.

Persists knowledge records to a SQLite database so the ecosystem's corpus
survives across process runs. Uses:
  - WAL journal mode for concurrent readers
  - A JSON column storing the full KnowledgeRecordV0 (round-trips losslessly)
  - A tag table for fast tag queries
  - An FTS5 virtual table for full-text content search (graceful fallback to a
    LIKE scan if the SQLite build lacks FTS5)

The shell contracts (contracts.py) are unchanged — this is a pure flesh swap.
Stdlib only (``sqlite3``); no third-party dependency.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import Iterator

from src.mouseion.backends.base import KnowledgeBackend
from src.mouseion.contracts import KnowledgeRecordV0
from src.utils.helpers import get_logger

logger = get_logger("mouseion.sqlite")


class SQLiteBackend(KnowledgeBackend):
    """Durable SQLite-backed knowledge store."""

    name = "sqlite"

    def __init__(self, path: str = "mouseion.db") -> None:
        self.path = path
        # check_same_thread=False + our own lock → safe across the sim's threads.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._has_fts = False
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge (
                    record_id   TEXT PRIMARY KEY,
                    author_id   TEXT,
                    content     TEXT,
                    confidence  REAL,
                    created_ms  INTEGER,
                    data        TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_tags (
                    record_id TEXT,
                    tag       TEXT,
                    PRIMARY KEY (record_id, tag)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tags_tag ON knowledge_tags(tag)"
            )
            # FTS5 is optional — degrade gracefully if the build lacks it.
            try:
                self._conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts "
                    "USING fts5(record_id UNINDEXED, content)"
                )
                self._has_fts = True
            except sqlite3.OperationalError:
                self._has_fts = False
                logger.warning("SQLite build lacks FTS5; falling back to LIKE scan")
            self._conn.commit()

    # ------------------------------------------------------------------
    # KnowledgeBackend API
    # ------------------------------------------------------------------

    def put(self, record: KnowledgeRecordV0) -> None:
        payload = record.model_dump_json()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO knowledge "
                "(record_id, author_id, content, confidence, created_ms, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (record.record_id, record.author_id, record.content,
                 record.confidence, record.created_at_ms, payload),
            )
            self._conn.execute(
                "DELETE FROM knowledge_tags WHERE record_id = ?", (record.record_id,)
            )
            self._conn.executemany(
                "INSERT OR IGNORE INTO knowledge_tags (record_id, tag) VALUES (?, ?)",
                [(record.record_id, t) for t in record.topic_tags],
            )
            if self._has_fts:
                self._conn.execute(
                    "DELETE FROM knowledge_fts WHERE record_id = ?", (record.record_id,)
                )
                self._conn.execute(
                    "INSERT INTO knowledge_fts (record_id, content) VALUES (?, ?)",
                    (record.record_id, record.content),
                )
            self._conn.commit()

    def get(self, record_id: str) -> KnowledgeRecordV0 | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM knowledge WHERE record_id = ?", (record_id,)
            ).fetchone()
        return KnowledgeRecordV0.model_validate_json(row["data"]) if row else None

    def query_by_tag(self, tag: str) -> list[KnowledgeRecordV0]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT k.data FROM knowledge k "
                "JOIN knowledge_tags t ON k.record_id = t.record_id "
                "WHERE t.tag = ? ORDER BY k.created_ms",
                (tag,),
            ).fetchall()
        return [KnowledgeRecordV0.model_validate_json(r["data"]) for r in rows]

    def all(self) -> Iterator[KnowledgeRecordV0]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM knowledge ORDER BY created_ms"
            ).fetchall()
        return iter([KnowledgeRecordV0.model_validate_json(r["data"]) for r in rows])

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM knowledge").fetchone()
        return int(row["n"])

    def search(self, text: str, limit: int = 10) -> list[KnowledgeRecordV0]:
        if self._has_fts:
            with self._lock:
                try:
                    rows = self._conn.execute(
                        "SELECT k.data FROM knowledge_fts f "
                        "JOIN knowledge k ON k.record_id = f.record_id "
                        "WHERE knowledge_fts MATCH ? LIMIT ?",
                        (text, limit),
                    ).fetchall()
                    return [KnowledgeRecordV0.model_validate_json(r["data"]) for r in rows]
                except sqlite3.OperationalError:
                    pass  # malformed FTS query → fall through to substring scan
        return super().search(text, limit)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
