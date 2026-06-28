"""
tests/test_persistent_mouseion.py

Tests for the pluggable Mouseion backends and semantic search.

Covers:
  - Backend protocol parity (MemoryBackend and SQLiteBackend behave identically)
  - SQLite durability across Mouseion instances
  - FTS / substring full-text search
  - Vector store semantic retrieval (offline HashingEmbedder)
  - Zero breaking changes: the default Mouseion still uses MemoryBackend
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.mouseion.backends import (
    HashingEmbedder,
    MemoryBackend,
    SQLiteBackend,
    VectorStore,
)
from src.mouseion.contracts import KnowledgeRecordV0
from src.mouseion.substrate import Mouseion
from src.utils.helpers import content_hash, new_id


def _record(content: str, tags: list[str], confidence: float = 0.8) -> KnowledgeRecordV0:
    return KnowledgeRecordV0(
        record_id=new_id("kr_"),
        author_id="tester",
        content=content,
        content_hash=content_hash(content),
        topic_tags=tags,
        confidence=confidence,
    )


@pytest.fixture
def sqlite_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Backend protocol parity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("make_backend", [
    lambda p: MemoryBackend(),
    lambda p: SQLiteBackend(p),
])
def test_backend_put_get(make_backend, sqlite_path):
    backend = make_backend(sqlite_path)
    rec = _record("hello world", ["greeting"])
    backend.put(rec)
    got = backend.get(rec.record_id)
    assert got is not None
    assert got.content == "hello world"
    assert got.topic_tags == ["greeting"]
    backend.close()


@pytest.mark.parametrize("make_backend", [
    lambda p: MemoryBackend(),
    lambda p: SQLiteBackend(p),
])
def test_backend_query_by_tag(make_backend, sqlite_path):
    backend = make_backend(sqlite_path)
    backend.put(_record("a", ["x", "shared"]))
    backend.put(_record("b", ["shared"]))
    backend.put(_record("c", ["y"]))
    assert len(backend.query_by_tag("shared")) == 2
    assert len(backend.query_by_tag("x")) == 1
    assert backend.query_by_tag("missing") == []
    backend.close()


@pytest.mark.parametrize("make_backend", [
    lambda p: MemoryBackend(),
    lambda p: SQLiteBackend(p),
])
def test_backend_count_and_all(make_backend, sqlite_path):
    backend = make_backend(sqlite_path)
    for i in range(5):
        backend.put(_record(f"rec {i}", ["t"]))
    assert backend.count() == 5
    assert len(list(backend.all())) == 5
    backend.close()


@pytest.mark.parametrize("make_backend", [
    lambda p: MemoryBackend(),
    lambda p: SQLiteBackend(p),
])
def test_backend_search(make_backend, sqlite_path):
    backend = make_backend(sqlite_path)
    backend.put(_record("osimertinib treats EGFR lung cancer", ["onc"]))
    backend.put(_record("trastuzumab treats HER2 breast cancer", ["onc"]))
    hits = backend.search("osimertinib")
    assert any("osimertinib" in r.content for r in hits)
    backend.close()


def test_put_is_idempotent_on_tags(sqlite_path):
    """Re-putting the same record id must not duplicate tag rows."""
    backend = SQLiteBackend(sqlite_path)
    rec = _record("v1", ["a", "b"])
    backend.put(rec)
    rec2 = rec.model_copy(update={"content": "v2"})
    backend.put(rec2)
    assert backend.count() == 1
    assert len(backend.query_by_tag("a")) == 1
    assert backend.get(rec.record_id).content == "v2"
    backend.close()


# ---------------------------------------------------------------------------
# SQLite durability
# ---------------------------------------------------------------------------

def test_sqlite_persists_across_instances(sqlite_path):
    m1 = Mouseion(backend=SQLiteBackend(sqlite_path))
    m1.store_knowledge("author", "durable content", topic_tags=["persist"])
    assert m1.knowledge_count() == 1
    m1.close()

    # New Mouseion, same DB file → data survives.
    m2 = Mouseion(backend=SQLiteBackend(sqlite_path))
    assert m2.knowledge_count() == 1
    assert len(m2.query_knowledge("persist")) == 1
    m2.close()


# ---------------------------------------------------------------------------
# Mouseion integration
# ---------------------------------------------------------------------------

def test_default_mouseion_uses_memory_backend():
    m = Mouseion()
    assert m.backend_name == "memory"


def test_mouseion_with_sqlite_backend(sqlite_path):
    m = Mouseion(backend=SQLiteBackend(sqlite_path))
    assert m.backend_name == "sqlite"
    rec = m.store_knowledge("a", "content", topic_tags=["t"], confidence=0.9)
    assert m.get_knowledge(rec.record_id).confidence == 0.9
    m.close()


def test_mouseion_search_knowledge():
    m = Mouseion()
    m.store_knowledge("a", "RECIST imaging response criteria", topic_tags=["radiology"])
    m.store_knowledge("a", "BRCA germline testing", topic_tags=["genomics"])
    hits = m.search_knowledge("RECIST")
    assert any("RECIST" in r.content for r in hits)


# ---------------------------------------------------------------------------
# Vector store / semantic search
# ---------------------------------------------------------------------------

def test_hashing_embedder_is_deterministic():
    e = HashingEmbedder(dim=128)
    v1 = e.embed("EGFR lung cancer")
    v2 = e.embed("EGFR lung cancer")
    assert (v1 == v2).all()
    assert abs(float((v1 * v1).sum()) - 1.0) < 1e-5  # unit norm


def test_vector_store_ranks_by_similarity():
    vs = VectorStore()
    vs.add(_record("EGFR mutation in lung cancer treated with osimertinib", ["lung"]))
    vs.add(_record("HER2 positive breast cancer treated with trastuzumab", ["breast"]))
    vs.add(_record("the weather today is sunny and warm", ["weather"]))
    results = vs.query("lung cancer EGFR osimertinib", k=2)
    assert len(results) == 2
    # The lung-cancer record should rank first.
    assert "EGFR" in results[0][0].content
    assert results[0][1] >= results[1][1]  # sorted descending


def test_vector_store_empty_query():
    assert VectorStore().query("anything") == []


def test_mouseion_semantic_query():
    vs = VectorStore()
    m = Mouseion(vector_store=vs)
    m.store_knowledge("a", "EGFR mutation lung cancer osimertinib targeted therapy",
                      topic_tags=["lung"])
    m.store_knowledge("a", "palliative care quality of life end of life",
                      topic_tags=["palliative"])
    results = m.semantic_query("targeted therapy for EGFR lung cancer", k=1)
    assert len(results) == 1
    assert "EGFR" in results[0][0].content


def test_semantic_query_without_store_returns_empty():
    m = Mouseion()  # no vector store
    assert m.semantic_query("anything") == []


def test_attach_vector_store_indexes_existing(sqlite_path):
    """Loading a pre-populated backend then attaching a vector store re-indexes."""
    m1 = Mouseion(backend=SQLiteBackend(sqlite_path))
    m1.store_knowledge("a", "EGFR lung cancer", topic_tags=["lung"])
    m1.store_knowledge("a", "HER2 breast cancer", topic_tags=["breast"])
    m1.close()

    m2 = Mouseion(backend=SQLiteBackend(sqlite_path))
    n = m2.attach_vector_store(VectorStore())
    assert n == 2
    results = m2.semantic_query("lung cancer EGFR", k=1)
    assert "EGFR" in results[0][0].content
    m2.close()
