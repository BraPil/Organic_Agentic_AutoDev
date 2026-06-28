# Persistent Mouseion

Swaps the Mouseion's in-memory knowledge store for durable storage, and adds
semantic vector search — without changing the Mouseion's public API or any
caller. A pure MoltBook flesh swap.

## Status

✅ Implemented on `feature/persistent-mouseion`. 19 new tests; full suite 201
passing. Zero breaking changes — the default Mouseion still uses `MemoryBackend`.

## Module map (`organic_agentic_autodev/mouseion/backends/`)

| File | Role | Shell/Flesh |
|------|------|-------------|
| `base.py` | `KnowledgeBackend` abstract contract | Shell |
| `memory_backend.py` | `MemoryBackend` — in-memory default | Flesh |
| `sqlite_backend.py` | `SQLiteBackend` — durable (WAL + FTS5), stdlib only | Flesh |
| `vector_store.py` | `VectorStore` + embedders | Flesh (additive) |

## What changed in `Mouseion`

The knowledge store was extracted behind `KnowledgeBackend`. `Mouseion.__init__`
gained two optional parameters:

```python
Mouseion(backend=..., vector_store=...)
```

- `backend` defaults to `MemoryBackend()` → identical behaviour to before.
- `vector_store` defaults to `None` → semantic search disabled until attached.

The Mouseion still owns sanitisation, hashing, record construction, and event
emission; the backend only persists and retrieves fully-formed records.

New methods (all additive):

| Method | Purpose |
|--------|---------|
| `search_knowledge(text, limit)` | Full-text search (FTS5 on SQLite, scan otherwise) |
| `semantic_query(text, k)` | Vector similarity search (needs a vector store) |
| `attach_vector_store(vs)` | Attach + index existing records (for loaded backends) |
| `close()` | Release backend resources (closes the SQLite connection) |
| `backend_name` | Property: active backend name |

## SQLite backend

- WAL journal mode (concurrent readers)
- Full `KnowledgeRecordV0` stored as JSON (lossless round-trip via Pydantic)
- Separate tag table with an index for fast tag queries
- FTS5 virtual table for content search, with graceful fallback to a `LIKE`
  scan if the SQLite build lacks FTS5
- Pure stdlib (`sqlite3`) — no third-party dependency

```python
from organic_agentic_autodev.mouseion.backends import SQLiteBackend
from organic_agentic_autodev.mouseion.substrate import Mouseion

m = Mouseion(backend=SQLiteBackend("mouseion.db"))
m.store_knowledge("agent", "durable finding", topic_tags=["research"])
m.close()

# Later / another process — same file, data survives:
m2 = Mouseion(backend=SQLiteBackend("mouseion.db"))
assert m2.knowledge_count() == 1
```

## Semantic search

`VectorStore` is brute-force cosine similarity over numpy vectors with a
pluggable `Embedder`:

- **`HashingEmbedder`** (default) — deterministic, dependency-free,
  process-independent (blake2b feature hashing). Runs offline with zero config
  and gives meaningful similarity for topical overlap. Reproducible in tests.
- **`SentenceTransformerEmbedder`** (optional) — real semantic embeddings if
  `sentence-transformers` is installed (`pip install -e ".[vector]"`). Drop-in:
  nothing else changes.

The numpy brute-force index is correct and fast at POC scale; FAISS/Qdrant can
replace the index behind the same `VectorStore` interface for scale.

```python
from organic_agentic_autodev.mouseion.backends import VectorStore

m = Mouseion(vector_store=VectorStore())
m.store_knowledge("agent", "EGFR lung cancer osimertinib", topic_tags=["lung"])
for record, score in m.semantic_query("targeted therapy for EGFR lung cancer", k=3):
    print(score, record.content)
```

## Demo

```bash
python examples/persistence_demo.py
```

Shows SQLite durability across instances, FTS5 search, and semantic retrieval.

## Environment variables (see runbook)

| Variable | Purpose | Default |
|----------|---------|---------|
| `OAAD_MOUSEION_BACKEND` | `memory` / `sqlite` | `memory` |
| `OAAD_MOUSEION_DB` | SQLite DB path | `mouseion.db` |
