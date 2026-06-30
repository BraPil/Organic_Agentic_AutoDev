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

---

### 2026-06-30 — Phase 2 sequencing + slice C: wiki health → observability SLI

**Decision:** Open Phase 2 with the candidate **sequence C → A, deferring B**, after weighing all three against the constitution: (A) FAISS vector retrieval — the headline, kept offline via `faiss-cpu` + deterministic `HashingEmbedder`; (B) Postgres backend — **deferred** as premature optimization that fights the offline-first test mandate (needs a live server); (C) wire `lint`/`query` health into the SLI/SLO framework — done first because it's the smallest change, serves the top-ranked Observability value, and gives a grounding **baseline to measure A against** (instrument before optimizing, rank 2). Built slice C as `WikiHealthMonitor` + `build_wiki_health_sla()` in a new `observability/wiki_health.py` (flesh): a **passive observer** that reuses the existing shell contracts (`SLIMeasurementV0`/`SLODefinitionV0`/`SLOEvaluationV0`), writes nothing back, and exposes four SLIs — `wiki_link_integrity` (GTE 1.0), `wiki_orphan_rate` (LTE 0.0), `wiki_contradiction_count` (LTE 0.0/at-risk ≤2), `query_grounding_rate` (GTE 0.80, INSUFFICIENT_DATA without probes). Added four additive `SLIKind` enum members (shell edit, authorized). `lint`'s **stubs** are deliberately *not* gated by an SLO (advisory, not a breach).

**Why:** Honors offline-first + determinism (10 new tests, 300 total, no API key) and the pristine-core rule — no consumer glue, no new dependency, the only shell touch is additive enum members + `__init__` exports. A separate monitor (not bolted onto the ecosystem `SLITracker`) keeps the tick-based ecosystem observer decoupled from the wiki's lint-cadence observer (Simplicity, Replaceability). Surfacing health as an SLI realizes "if it isn't measured, it doesn't exist" for the knowledge layer.

**Consequences:** Phase 2 is IN PROGRESS (slice C complete; A — FAISS retrieval — is next, with the D answer-reuse thread folded in and measured against the new `query_grounding_rate` baseline). The grounding SLI is inert until a consumer supplies probe questions — by design (generic engine, no domain-specific probes baked in). Phase 1 was merged to `main` (`--no-ff`) and pushed before this branch (`feature/wiki-observability-sli`) opened, per the merge-first phase-transition workflow.

---

### 2026-06-30 — Phase 2 slice A: pluggable wiki retrieval (vector seam), FAISS deferred

**Decision:** Reframe slice A from "add FAISS" to **"give the wiki a pluggable `Retriever` strategy"** and **do not add `faiss-cpu`**. Investigation showed the existing `mouseion/backends/vector_store.py` already provides the vector seam (`Embedder` protocol, deterministic offline `HashingEmbedder`, optional `SentenceTransformerEmbedder`, brute-force cosine `VectorStore`) and explicitly names FAISS/Qdrant as a future *scale* swap *behind that interface*. So FAISS is a scale optimization with no measured scale problem — the same premature-optimization trap that deferred Postgres (slice B). Built instead a `Retriever` ABC in `knowledge_wiki/retrieval.py` with `LexicalRetriever` (default — Phase 1 behavior byte-for-byte) and `VectorRetriever` (opt-in cosine over an injectable `Embedder`, default `HashingEmbedder`). `KnowledgeWiki` gains a `retriever=` param (mirrors `cognition=`); `query()` delegates ranking to it. `VectorRetriever.min_similarity` defaults to a conservative **0.3** (see discovery-log 2026-06-30: feature-hash collision noise ~0.25 rivals weak real signal ~0.27, so favor precision over recall; real embedders warrant a lower threshold).

**Why:** Honors Simplicity ("no future-proofing"), Correctness ("measure before optimizing"), and Replaceability — delivers the Phase 2 "Retrieval" capability and the swap-seam with **zero new dependencies** (numpy is already core) while staying fully offline + deterministic (10 new tests, 310 total). Defaulting to lexical keeps every Phase 1 query/lint test valid (no behavior regression). Consumers needing real semantic retrieval inject `SentenceTransformerEmbedder`; consumers needing scale drop FAISS/Qdrant behind `VectorStore` — both without touching the wiki.

**Consequences:** Phase 2 slices A + C complete. FAISS/Qdrant and a Postgres backend remain deferred until a measured scale need (record it as a superseding entry when that need is real). Honest scope note: with the default `HashingEmbedder`, `VectorRetriever` is a demonstrable *seam*, not a retrieval-quality win over lexical — the quality gain requires real embeddings. The **D answer-reuse thread** (promoted `wiki:answer` records re-retrieved by `query`) was **not** folded in — kept as its own future slice to keep this change focused (DoD: split large tasks); it now has a clean home behind the `Retriever` seam.

---

### 2026-06-30 — Phase 2 slice D: answer-reuse closes the compounding loop

**Decision:** Make promoted `wiki:answer` records *retrievable* (Karpathy's "valuable answers compound" — they were write-only, accumulating as dead records). `query(reuse_answers=True)` (default) re-ranks prior answers through the **same `Retriever`** as a *transient* page corpus (wrapped as `WikiPage`s, never stored in `self._pages`, so they stay out of the lint link-graph — one retrieval mechanism, not two), reports matches in a new `QueryResult.reused_answers` field, and threads those ids into the next promotion's `provenance_refs`. Three deliberate guardrails: (1) page composition is **untouched** — reused answers are a structured signal + provenance link, not merged prose, so promoted content never drifts answer-on-answer; (2) `grounded` stays **strictly page-based** so it doesn't inflate the slice-C grounding SLI as answers accumulate; (3) reuse is computed *before* this query's own promotion, so a query never reuses itself.

**Why:** Smallest change that closes the loop (Simplicity) while protecting correctness — no content feedback, no metric inflation, stable provenance. Reusing the existing `Retriever` seam (instead of a parallel answer-ranking path) keeps lexical/vector strategies applying uniformly to pages and answers. Fully offline + deterministic (7 new tests, 317 total).

**Consequences:** Phase 2 slices A + C + D complete. The compounding graph is now traceable (new answer → reused prior answers → original sources). Two honest follow-ups left open: richer reuse could fold a strong prior-answer *into* composition or short-circuit recomputation (a cache), and near-duplicate promotions are not yet deduped — both deferred as they need a reliable similarity threshold (cf. the `HashingEmbedder` noise discovery, 2026-06-30). Remaining Phase 2 candidate: Postgres backend (still deferred, premature).

---

### 2026-06-30 — Phase 2 → Phase 3 transition; slice P3.1: LLM cognition in autoresearch proposals

**Decision:** Treat Phase 2 as **core-complete with Postgres deferred** and open **Phase 3 (cognition depth)**, per explicit user direction. First slice: add a `ProposalCognition` seam to autoresearch (`autoresearch/cognition.py`) — `HeuristicProposalCognition` (default, random ordering through the Proposer's seeded RNG) + `LLMProposalCognition` (behind the bridge `CognitionProvider`, falls back to heuristic on any failure). The `Proposer` delegates **strategy** (which experiment type to try first + a data-grounded `rationale`) to the cognition, while keeping **all mechanics in code**: value bounds/clamps and the compassion guard never move into the cognition. Cognition output is sanitized — its ordering is filtered to actually-available types and any omitted types are still appended, so it can reorder but never remove options or inject an invalid/unsafe one.

**Why:** Honors the established cognition pattern (ABC + deterministic offline default + graceful LLM, mirroring `WikiCognition` and the bridge) and the offline-first mandate (9 new tests, 326 total, stub provider — no network). Critically, **compassion-as-first-class is enforced structurally**: because bounds + the guard live in the Proposer, an LLM (or a buggy/adversarial one) cannot ship a starving/lethal/destabilising experiment — the worst it can do is reorder safe options. Additive flesh: no shell contract changed (only additive `__init__` exports); the default behavior (and every existing autoresearch test) is unchanged because the default heuristic shares the RNG.

**Consequences:** Phase 3 in progress. Natural next slices (still guard-bounded): let cognition choose perturbation *direction/magnitude* (not just order), and enrich the prompt context with fitness trend / energy headroom so the rationale is genuinely data-driven. As with the wiki LLM paths, real-model behavior is validated out-of-band (discovery-log), never in CI.
</content>
