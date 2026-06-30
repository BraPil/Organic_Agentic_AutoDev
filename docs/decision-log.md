# Decision Log

Chronological record of architectural decisions. Newest at the bottom of each block.
Each entry: **what** was decided, **why**, and **consequences**. Reverse a decision only with a new dated entry that references the one it supersedes.

Format: `### YYYY-MM-DD — <title>` · **Decision** · **Why** · **Consequences**.

---

### 2026-06-28 — Package layout: `organic_agentic_autodev`, src-layout

**Decision:** The importable package is `organic_agentic_autodev` (not `src`). Imports are `from organic_agentic_autodev.X`. `pyproject` uses `include = ["organic_agentic_autodev*"]`. Console script `oaa-learning-cycle` → `organic_agentic_autodev.cognition.run_cycle:main`.

**Why:** A top-level `src` package collided with AAA's own `src/`, which embeds this repo as its P6 learning engine. The rename makes OAA cleanly embeddable.

**Consequences:** Any consumer or doc referencing `src.*` is stale and must be updated. Shell `__init__.py` exports are the stable public API.

---

### 2026-06-28 — Tech stack baseline

**Decision:** Python 3.11+; SQLite (WAL + FTS5, stdlib) for durable storage with an in-memory `MemoryBackend` default; deterministic `HashingEmbedder` (blake2b) for offline vector search with optional `sentence-transformers`; Anthropic SDK as default LLM provider with OpenAI optional; `pytest` for tests; `structlog` + an SLI/SLO/SLA tracker for observability; `ruff` + `mypy` for lint/types.

**Why:** Every default must run offline with no API keys so CI stays green and consumers can clone-and-run. Heavier engines (FAISS, Postgres, real LLMs) are optional flesh behind stable seams.

**Consequences:** Tests never make live API calls. New dependencies require an entry here. Optional extras: `[llm] [vector] [dashboard] [distributed] [dev]`.

---

### 2026-06-28 — Cognition bridge confidence = mean critic score

**Decision:** The cognition bridge (`cognition/bridge.py` + `run_cycle.py`) runs a Researcher→Critic→Synthesizer `LearningCycle` and emits `KnowledgeRecordV0` JSONL — the generic OAA→consumer boundary. Finding confidence is the **mean of adversarial critic scores**, not a self-rated value.

**Why:** Self-rated confidence is unreliable; an adversarial mean is harder to game and is what AAA's 0.70 acceptance gate expects. Live-validated: a 3R/2C/1S cycle produced synthesis confidence 0.80.

**Consequences:** The bridge is the contract consumers depend on; changing the scoring or the `KnowledgeRecordV0` schema is a shell change requiring approval. Default bridge model is `claude-haiku-4-5-20251001`; `DeterministicCognition` backs offline tests.

---

### 2026-06-29 — OAA positioning: standalone cloneable engine

**Decision:** OAA is its own standalone, pristine, generic self-improving agentic-swarm engine/template. It is NOT a subcomponent of AAA. Consumer-specific glue (AAA, ExMorbus) belongs in the consumer repos, never in OAA core.

**Why:** Multiple consumers (AAA's P6 engine, an upcoming ExMorbus update, others) need to embed the same clean engine. Leaking consumer glue into core would couple them and break reuse.

**Consequences:** Core modules must stay generic (grep-verifiable). The package import and the JSONL cognition bridge are the two stable integration seams. Released as v0.2.0.

---

### 2026-06-29 — Adopt the Karpathy compounding-knowledge-wiki pattern as Phase 1

**Decision:** Adopt Karpathy's LLM-maintained-wiki pattern (raw sources → LLM-owned wiki → load-bearing schema, with **ingest / query / lint** operations) and build it operationally over the Mouseion knowledge layer as the headline of Phase 1. The schema doc lives in `docs/knowledge.md`; design rationale in `adr/ADR-0001-compounding-knowledge-wiki.md`.

**Why:** OAA's Mouseion is already an LLM-curated, compounding knowledge substrate; the pattern gives it a disciplined ingest/query/lint lifecycle and a shared vocabulary. It also formalizes how this repo's own `docs/` are maintained (LLM does the bookkeeping; human curates sources and asks questions).

**Consequences:** Phase 1 work must keep the build offline-testable via the deterministic provider. The pattern governs both the runtime knowledge layer and the docs-tracking discipline going forward. Companion-doc set created this session to support tracking.

---

### 2026-06-29 — Knowledge-wiki ingest (P1.2): design choices

**Decision:** Implement `ingest` in a new self-contained `organic_agentic_autodev/knowledge_wiki/` package with these choices: (1) **no shell changes** — wiki pages persist as existing `KnowledgeRecordV0` (tags `wiki:source` for immutable sources, `wiki:page` for page snapshots with provenance refs); no new `EventKind`, no `contracts.py` edits, no changes to existing `__init__` exports. (2) **Synthesis lives in a `WikiCognition` seam**, not the orchestrator — `KnowledgeWiki` only applies `PageOp`s and persists (thin orchestrator). (3) **`DeterministicWikiCognition` is the default**; `LLMWikiCognition` wraps the bridge `CognitionProvider` and falls back to deterministic on any failure. (4) **Contradiction policy = flag-and-keep**: a conflicting claim (same key, different value) is surfaced in `IngestResult` + an accumulated log and the *existing* value is preserved — never silently overwritten.

**Why:** Honors the pristine-core / additive-flesh rule and the offline-first mandate (22 tests, no API key). The cognition seam keeps the orchestrator from becoming a fat transformer (anti-pattern). Flag-and-keep is the conservative choice: resolution belongs to a human or to the upcoming `lint`/`query` phase, not to a blind last-writer-wins overwrite.

**Consequences:** P1.3 `lint` already has its inputs (the contradiction log + page link graph). If flag-and-keep proves too conservative (stale pages persist), revisit with a confidence- or recency-based resolver and record a superseding entry. Page snapshots are append-only per version (provenance history); acceptable bloat for now.

---

### 2026-06-29 — Knowledge-wiki query + lint (P1.3): design choices

**Decision:** Complete Phase 1 with `query` and `lint`. (1) **Retrieval is deterministic lexical overlap** (`retrieval.relevance`: title 3×, claims 2×, body 1×, normalized by question-token count) in a separate pure module — keeping ranking testable and the orchestrator thin; vector retrieval is a Phase 2 swap behind the same signature. (2) **Grounded answers are promoted** into the Mouseion as `wiki:answer` `KnowledgeRecordV0` with provenance to the sources the answer drew on; ungrounded questions (no page match) are never promoted; `promote=False` opts out. (3) **Lint is structural and deterministic** — orphans (only when >1 page), dangling links, missing concepts, the contradiction log, and stubs. Wall-clock staleness is deferred (it would make lint non-deterministic, violating the no-wall-clock-in-logic invariant; it needs a tick/version baseline). (4) `answer()` added to the `WikiCognition` ABC with a shared deterministic composer + an LLM path that falls back on failure.

**Why:** Honors offline-first + determinism (39 wiki tests total, no API key) and the thin-orchestrator rule. Promotion realizes Karpathy's "valuable answers compound" without polluting the page namespace (answers are durable records, not navigable pages). Deferring wall-clock staleness keeps lint honest rather than shipping a non-reproducible check.

**Consequences:** Phase 1 (ingest/query/lint) is COMPLETE. Phase 2 candidates: real vector retrieval behind `relevance`, a Postgres backend, and surfacing `lint` health as an observability SLI. Promoted answers are not yet re-retrieved by `query` (retrieval is over pages only) — a future enhancement if answer-reuse proves valuable.
</content>
