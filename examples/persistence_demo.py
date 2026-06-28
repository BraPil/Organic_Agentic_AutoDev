"""
examples/persistence_demo.py

Persistent Mouseion — demonstration.

Shows two capabilities:
  1. SQLite durability — knowledge written by one Mouseion instance is read back
     by a second instance pointing at the same database file.
  2. Semantic search — retrieve records by meaning via the offline vector store.

Run:
    python examples/persistence_demo.py
"""

from __future__ import annotations

import logging
import os
import tempfile

logging.basicConfig(level=logging.WARNING)

from src.domain.exmorbus import seed_mouseion
from src.mouseion.backends import SQLiteBackend, VectorStore
from src.mouseion.substrate import Mouseion


def main() -> None:
    print("=" * 70)
    print("  💾  Persistent Mouseion Demo")
    print("=" * 70)

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        # --- Instance 1: seed and persist to SQLite ---
        print(f"\n  [1] Writing to SQLite backend: {db_path}")
        m1 = Mouseion(backend=SQLiteBackend(db_path))
        seed_mouseion(m1)
        print(f"      Seeded {m1.knowledge_count()} oncology records (durable)")
        m1.close()

        # --- Instance 2: reopen the SAME database ---
        print("\n  [2] Reopening the database in a fresh Mouseion instance")
        m2 = Mouseion(backend=SQLiteBackend(db_path))
        print(f"      Read back {m2.knowledge_count()} records — data survived the restart ✓")

        # --- Full-text search (FTS5) ---
        print("\n  [3] Full-text search for 'osimertinib':")
        for rec in m2.search_knowledge("osimertinib", limit=2):
            print(f"      • {rec.content[:80]}…")

        # --- Semantic search (offline vector store) ---
        print("\n  [4] Attaching vector store and running semantic queries")
        indexed = m2.attach_vector_store(VectorStore())
        print(f"      Indexed {indexed} records for semantic search")

        for query in [
            "targeted therapy for lung cancer with EGFR mutations",
            "managing severe immune-related side effects",
            "early supportive and end-of-life care",
        ]:
            print(f"\n      Query: \"{query}\"")
            for rec, score in m2.semantic_query(query, k=2):
                print(f"        [{score:.3f}] {rec.content[:72]}…")

        m2.close()
        print("\n  Done.\n")
    finally:
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(db_path + suffix)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    main()
