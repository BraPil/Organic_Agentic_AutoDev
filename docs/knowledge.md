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

## The wiki lifecycle: ingest / query / lint (Phase 1)

Three operations, each offline-testable via the deterministic provider. Code lives in
`organic_agentic_autodev/knowledge_wiki/` (`KnowledgeWiki` orchestrator + a `WikiCognition`
synthesis seam with `DeterministicWikiCognition` default and `LLMWikiCognition` live impl).
Demo: `examples/knowledge_wiki_demo.py`.

### Ingest — ✅ implemented (P1.2)
`KnowledgeWiki.ingest(source)` triggers wiki maintenance across the related pages:
- stores the raw source immutably as a `KnowledgeRecordV0` tagged `wiki:source`,
- synthesizes it into the wiki layer (a `WikiPage`, not a verbatim copy) — the cognition layer
  decides the page ops; the orchestrator only applies them,
- cross-references it against existing pages (links by title/slug match),
- detects contradictions (same claim key, different value) and **surfaces them, keeping the
  existing value pending review** — never a silent overwrite,
- snapshots each page version to a `KnowledgeRecordV0` tagged `wiki:page` with provenance back to
  its sources.

### Query — ✅ implemented (P1.3); pluggable retrieval added (Phase 2, slice A)
`KnowledgeWiki.query(question)` retrieves the relevant pages through a swappable `Retriever`
(`retrieval.py`): `LexicalRetriever` (default — deterministic weighted token overlap, title 3×, claims
2×, body 1×) or `VectorRetriever` (cosine over the existing `Embedder`/`HashingEmbedder`; inject
`SentenceTransformerEmbedder` for real semantics, or FAISS/Qdrant behind `VectorStore` for scale) and composes an answer from them. **A grounded answer is promoted into the durable
store** (tagged `wiki:answer`, with provenance to the sources it drew on) instead of vanishing into
chat history — the "compounding" mechanism. `promote=False` opts out; an ungrounded question (no
matching page) is never promoted.

### Lint — ✅ implemented (P1.3)
`KnowledgeWiki.lint()` is a deterministic structural health check over the wiki layer, surfacing:
- **orphans** — pages disconnected from the link graph (only flagged when >1 page),
- **dangling links** — links pointing at a slug with no page,
- **missing concepts** — the unique referenced-but-absent slugs (Karpathy's "missing concepts"),
- **contradictions** — the accumulated unresolved-conflict log,
- **stubs** — under-developed pages (no claims + short body).

`LintReport.healthy`/`summary()` make the result measurable (counts per category) for
`docs/evaluation.md` SLIs. *Wall-clock staleness is deferred* — it needs a tick/version baseline, and
lint must stay deterministic.

**Health as an SLI (Phase 2, slice C):** `lint`/`query` health is now wired into the observability
SLI/SLO framework via `WikiHealthMonitor` (`observability/wiki_health.py`) — a passive observer that
turns a `lint()` pass + probe `query()`s into four SLIs (link integrity, orphan rate, contradiction
count, query grounding) evaluated against `build_wiki_health_sla()`. See `docs/evaluation.md`.

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
