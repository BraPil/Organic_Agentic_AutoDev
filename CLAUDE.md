# CLAUDE.md — Organic Agentic AutoDev (OAA)

> Governs every AI coding session in this repository.
> Read before touching any file. Keep lean — depth lives in companion docs.
> **When this file conflicts with the code, the code wins. Update this file immediately.**

---

## 0. Ecosystem Map

| Companion File | Governs |
|----------------|---------|
| `docs/architecture.md` | System design, component map, data flows, phase roadmap |
| `docs/governance.md` | Protected paths, approval escalation, file ownership |
| `docs/workflows.md` | Dev lifecycle, branching, commit standards, PR process |
| `docs/evaluation.md` | AI/ML eval methodology, benchmark tracking, uncertainty policy |
| `docs/security.md` | Threat model, injection defense, secret hygiene |
| `docs/knowledge.md` | Knowledge types, storage strategy, retrieval patterns, the compounding-wiki model |
| `docs/decision-log.md` | Chronological record of architectural decisions |
| `docs/discovery-log.md` | Important findings that affect future work |
| `docs/lessons-learned.md` | Mistakes, surprises, preventive lessons |
| `adr/` | Architecture Decision Records (created on demand) |
| `docs/roadmap.md` | Full feature design detail (carried over from Phase 0) |
| `docs/wiki.md` | Concept index + "where does X live" navigation hub |

*Read only the companions relevant to the current session's task.*

---

## 1. Mission

**Purpose:** OAA is a standalone, pristine, self-improving agentic-swarm engine/template — a bio-mimicking architecture (stem cells → cells → organs → body, with Physarum slime-mold network topology) that other projects clone or embed when they need a self-improving swarm environment.

**Users:** Other software projects and their agents — primarily `BraPil/Agentic-AI-Architect` (AAA), which embeds OAA as its P6 learning engine; an upcoming ExMorbus update; and other consumers. Also the human maintainer working directly in this repo. Consumption happens at two seams: cloning/embedding the package, and the cognition bridge (`run_cycle.py` → `KnowledgeRecordV0` JSONL).

**Success looks like:**
- The repo stays **pristine and generic** — zero AAA-specific or ExMorbus-specific glue leaks into core modules (verifiable by grep + review).
- The test suite stays **green and fully offline** (currently 300 passing; CI green on py3.11/3.12 with no API keys).
- Consumers integrate via the stable seams (package import + JSONL bridge) **without forking** core contracts.

**Non-goals (explicit):**
- OAA does **not** carry consumer-specific business logic (no AAA/ExMorbus glue in core).
- OAA does **not** require live LLM API keys, network access, or external services to run or test — those are always optional flesh.
- OAA is **not** a subcomponent of AAA; it is its own thing that AAA happens to consume.

---

## 2. Architectural Constitution

*Values, not rules. When two values conflict, the one ranked higher wins.*
*Derive correct behavior for novel situations from these values rather than asking for a rule.*

| Rank | Value | What it demands |
|------|-------|----------------|
| 1 | **Observability** | If it isn't logged and measurable, it doesn't exist |
| 2 | **Correctness** | Working before fast before elegant. Measure before optimizing |
| 3 | **Simplicity** | Smallest change satisfying the requirement. No future-proofing |
| 4 | **Explainability** | Every decision has a stated reason. No magic |
| 5 | **Testability** | If you can't test it, rethink the design |
| 6 | **Replaceability** | Implementations are swappable; interfaces are stable (MoltBook shell/flesh) |
| 7 | **Security** | Sanitize, authenticate, rate-limit from day one |
| 8 | **Evolvability** | Today's choice doesn't lock out tomorrow's option |

> **Example conflict resolution:** Observability vs. Simplicity — adding a log line is rarely
> "too complex." Simplicity vs. Correctness — never skip a test to ship faster.

**OAA-specific invariants** (full list in `docs/wiki.md`): sanitize every string entering the Mouseion; seed all RNGs (tests reproducible + offline); resource pools conserve; differentiation is irreversible; compassion is a first-class genome trait and fitness dimension; agents act on local information only.

---

## 3. Governance

*Actions requiring explicit human approval before proceeding:*

| Action | Risk | Default |
|--------|------|---------|
| Delete or overwrite files outside the active task scope | Blast radius | **Block** |
| Change public interfaces, API contracts, or wire schemas (shell: `*/contracts.py`, `genome.py`, `signal.py`, `__init__.py` exports) | Downstream breakage | **Block** |
| Add new dependencies to `pyproject.toml` | Security + bloat | **Block** |
| Commit anything containing credentials, tokens, or keys | Irreversible leak | **Block** |
| Modify CI/CD (`.github/workflows/`) or deployment configuration | Affects all contributors | **Block** |
| Push to `main` or release branches | Requires human gate | **Block** |
| Make irreversible infrastructure changes (drop tables, etc.) | Disaster recovery | **Block** |
| Refactor code outside the active task's stated scope | Scope creep | **Ask** |
| Reference an API or library without citing its source | Hallucination risk | **Ask** |

**Rule:** When uncertain whether an action falls under a guardrail — pause and ask.
Full protected-path list and ownership: `docs/governance.md`.

---

## 4. Session Protocol

*Execute in order at the start of every coding session:*

1. **Orient to state** — `git status && git log --oneline -5`
2. **Confirm the baseline is clean** — `pytest tests/ -v` (must be green before any change)
3. **Read the relevant companion docs** from the Ecosystem Map for this task.
4. **Check institutional memory** — scan `docs/decision-log.md` and `docs/discovery-log.md` for entries affecting the current task. Honor prior decisions or explicitly reverse them (with a new log entry).
5. **Optional — ingest LLM engineering foundations** — if working on AI/LLM components, read Karpathy's LLM-wiki pattern (`https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`). It is the conceptual basis for the Phase 1 compounding-knowledge-wiki; see `docs/knowledge.md` and `adr/ADR-0001-compounding-knowledge-wiki.md`.

---

## 5. Definition of Done

*A task is not complete until every applicable box is checked. Binary — not negotiable.*

**Code**
- [ ] Tests pass; new code has at least one happy-path and one failure-path test
- [ ] Tests run offline with no API keys (route LLM paths through a mock/deterministic provider)
- [ ] No new `ruff` warnings introduced
- [ ] No hardcoded secrets, credentials, or API keys
- [ ] External content sanitized (`sanitize_text()`) before entering the Mouseion or any LLM prompt

**Documentation**
- [ ] Relevant companion docs updated to reflect changed behavior
- [ ] `docs/decision-log.md` updated if an architectural decision was made
- [ ] `docs/discovery-log.md` / `docs/lessons-learned.md` updated if something surprising happened
- [ ] ADR filed in `adr/` if a significant architectural choice was locked in

**Hygiene**
- [ ] No unresolved TODOs within the task's stated scope
- [ ] No dead code or commented-out blocks left behind
- [ ] PR / commit description explains *why*, not just *what*

*If a task is too large to satisfy all applicable criteria in one session, split the task.*

---

## 6. Core Anti-Patterns

*These feel correct but are wrong for this codebase. Recognize them. Refuse them.*

| Pattern | The Trap | The Rule |
|---------|----------|----------|
| **Consumer glue in core** | AAA/ExMorbus-specific logic in OAA modules | Keep core generic; glue lives in the consumer repo |
| **Shell churn** | Editing `contracts.py`/`genome.py`/`signal.py` for a feature | Prefer additive flesh; version-bump shell only when forced |
| **Inline LLM calls** | LLM call buried in a utility or pipeline function | LLM calls belong in providers/agents; inject via config |
| **Credential-dependent tests** | Tests that fail without `.env` present | All tests pass in a clean environment with no secrets |
| **Print debugging** | `print()` in `organic_agentic_autodev/` | Structured logging (`structlog`) only |
| **Premature abstraction** | Helper extracted for a single use case | Three similar lines > one leaky abstraction |
| **Sanitization bypass** | "This source is internal, skip `sanitize_text()`" | Sanitize everything that touches the Mouseion or a prompt |
| **Spec fiction** | Referencing an API/package without verifying it exists | Read the source. Cite the version |
| **Non-determinism** | Unseeded RNG, wall-clock in logic | Seed all RNGs; tests must be reproducible |

---

## 7. Technology Stack

| Layer | Choice | Rationale | Upgrade Path |
|-------|--------|-----------|--------------|
| Language | Python 3.11+ | Pattern matching, typing maturity; CI tests 3.11 + 3.12 | 3.12 already supported |
| Structured store | SQLite (WAL + FTS5), stdlib; `MemoryBackend` default | Zero-dep durable storage; offline | Postgres at scale (Phase 2) |
| Vector search | `HashingEmbedder` (blake2b, deterministic, offline) default; optional `sentence-transformers` | Tests stay offline + deterministic | FAISS / Qdrant (Phase 2) |
| LLM interface | Anthropic SDK default (`claude-haiku-4-5` bridge, `claude-opus-4-8` cell cognition); OpenAI optional | Provider-agnostic via config; mock for tests | Local OSS via same provider seam |
| Testing | `pytest` (+ `pytest-asyncio`, `pytest-cov`) | Standard, offline | — |
| Observability | `structlog` + SLI/SLO/SLA tracker (`observability/`) | Structured events + measurable objectives | OpenTelemetry at scale |
| Lint / types | `ruff`, `mypy` | Fast, standard | — |

*Adding a new dependency requires a reason here and an entry in `docs/decision-log.md`.*
*Optional extras: `[llm]` `[vector]` `[dashboard]` `[distributed]` `[dev]` — none required for core tests.*

---

## 8. Phase Status

```
Phase 0 — Foundation (substrate→evolution, 5 features, cognition bridge)   ✅ COMPLETE
Phase 1 — Compounding Knowledge Wiki (Karpathy ingest/query/lint)          ✅ COMPLETE
Phase 2 — Knowledge Scale & Retrieval (FAISS/Qdrant, Postgres backend)     🔶 IN PROGRESS  ← here
Phase 3 — Cognition Depth (LLM cognition inside autoresearch proposals)    ⬜ NOT STARTED
Phase 4 — Distributed Hardening (multi-machine deploy)                     ⬜ NOT STARTED
Phase 5 — Domain Grounding & Consumer Integration (deeper ExMorbus, APIs)  ⬜ NOT STARTED
```

**Phase 1 — complete** (`knowledge_wiki/`, 39 offline tests):
1. [P1.1] ✅ Load-bearing **schema doc** (`docs/knowledge.md`).
2. [P1.2] ✅ **ingest** — sources stored immutably, synthesized into wiki pages with cross-referencing + contradiction detection, page snapshots persisted with provenance.
3. [P1.3] ✅ **query** (relevant pages retrieved, grounded answers promoted to the durable store with provenance) + **lint** (orphans, dangling links, missing concepts, contradictions, stubs).

**Phase 2 — in progress** (sequence C → A, defer B):
- [C] ✅ **wiki health → observability SLI** — `WikiHealthMonitor` + `build_wiki_health_sla()` (`observability/wiki_health.py`, 10 offline tests). Four SLIs over `lint`/`query`: link integrity, orphan rate, contradiction count, query grounding. Passive observer reusing the shell SLI/SLO contracts; no new deps. Gives the grounding baseline that slice A is measured against.
- [A] ⬜ **FAISS vector retrieval** behind `retrieval.relevance` (offline via `faiss-cpu` + deterministic `HashingEmbedder`); fold in answer-reuse (promoted `wiki:answer` re-retrieval). ← next
- [B] ⬜ **Postgres `KnowledgeBackend`** — deferred (premature until real scale pressure; fights offline-first tests).

**Phase discipline:** do not implement features belonging to a later phase until the current
phase's success criteria are met. Phase definitions live in `docs/architecture.md`.

---

*Maintained by: Brandt Pileggi. Last updated: 2026-06-30.*
*Architecture decisions: `docs/decision-log.md` | Discovery log: `docs/discovery-log.md`*
</content>
</invoke>
