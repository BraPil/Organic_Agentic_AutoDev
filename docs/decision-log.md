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
</content>
