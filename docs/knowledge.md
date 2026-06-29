# Knowledge

Knowledge types, storage strategy, retrieval patterns, and the **compounding-knowledge-wiki model**
(Phase 1). This is the *load-bearing schema doc* in Karpathy's sense: it documents the conventions and
workflows that turn an LLM from a generic chatbot into a disciplined knowledge maintainer.

> Source pattern: Karpathy's LLM-maintained-wiki
> (`https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`). See `adr/ADR-0001`.

---

## The three layers

| Layer | Mutability | Owner | In OAA today |
|-------|-----------|-------|--------------|
| **Raw sources** | Immutable ground truth | Human / ingest feed | Source documents, seed records (`domain/exmorbus/seeder.py`), external research |
| **Wiki** | LLM-owned, actively maintained markdown / records | The LLM (bookkeeping) | The Mouseion knowledge store + the repo's own `docs/` |
| **Schema** | Human-curated config | Human | This file + CLAUDE.md conventions |

The core insight: *the tedious part of a knowledge base is the bookkeeping, not the reading or
thinking.* LLMs do the bookkeeping; humans curate sources, ask strategic questions, and provide
oversight. This applies both to OAA's runtime Mouseion **and** to how this repo's docs are maintained.

---

## Knowledge record types (runtime)

The Mouseion stores `KnowledgeRecordV0` records with provenance, tags, and an **adversarial confidence**
(mean critic score, gated at ≥ 0.70 by consumers). Domain specializations add typed records
(`MedicalKnowledgeRecordV0`, `TreatmentRecommendationV0`, `ClinicalTrialMatchV0`). All contracts are
shell (`mouseion/contracts.py`, `domain/exmorbus/contracts.py`) — changing them is governance-gated.

## Storage strategy

- **Structured store:** `MemoryBackend` (default) / `SQLiteBackend` (WAL + FTS5, stdlib). Pluggable via
  the `KnowledgeBackend` ABC. Postgres is the Phase 2 upgrade path.
- **Vector / semantic:** `VectorStore` + `HashingEmbedder` (blake2b, deterministic, offline) by default;
  optional `SentenceTransformerEmbedder`. FAISS/Qdrant is the Phase 2 swap (seam already exists).
- **Retrieval:** `search_knowledge()` (lexical/FTS) and `semantic_query()` (vector) on the Mouseion.

## Invariants

1. Every string entering the Mouseion passes `sanitize_text()` (also a security control).
2. Records carry provenance; confidence is adversarial, never self-rated.
3. Retrieval is query-based and local — no agent gets omniscient global state.

---

## The wiki lifecycle: ingest / query / lint (Phase 1, building)

Three operations, each offline-testable via the deterministic provider:

### Ingest
A new raw source triggers wiki maintenance across the related pages/records:
- synthesize the source into the wiki layer (don't just store it verbatim),
- cross-reference it against existing records (link related knowledge),
- detect contradictions with what's already known and flag/reconcile them,
- preserve provenance back to the immutable source.

### Query
A question retrieves relevant wiki pages/records rather than re-deriving from raw sources each time.
**A valuable answer is promoted into a new wiki entry** instead of disappearing into chat history —
this is the "compounding" mechanism: the knowledge base gets richer with use.

### Lint
Periodic health check over the wiki layer, surfacing:
- **staleness** — records whose sources have moved on,
- **orphans** — entries nothing links to,
- **contradictions** — records that disagree,
- **missing concepts** — gaps implied by the sources but not yet written.

Lint output is measurable (counts per category) and feeds `docs/evaluation.md` SLIs.

---

## How this governs the repo's own docs

This same discipline applies to the `docs/` tree:
- **Sources** are the code, commits, and conversations (immutable record of what happened).
- **Wiki** is `docs/` — the decision/discovery/lessons logs, architecture, and `docs/wiki.md` index.
  The LLM maintains them: every behavior change updates the relevant companion (DoD requirement).
- **Schema** is CLAUDE.md + this file — the conventions that keep the wiki disciplined.

When the code and a doc disagree, **the code wins** and the doc is corrected immediately (CLAUDE.md
header rule). That correction is itself a `lint` event.
</content>
