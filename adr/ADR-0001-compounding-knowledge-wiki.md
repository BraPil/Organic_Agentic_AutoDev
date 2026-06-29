# ADR-0001 — Compounding Knowledge Wiki (Karpathy ingest/query/lint pattern)

- **Status:** Accepted
- **Date:** 2026-06-29
- **Owner:** Brandt Pileggi
- **Phase:** 1 (current)
- **Related:** `docs/knowledge.md` (schema), `docs/decision-log.md` (2026-06-29 entry), CLAUDE.md §8

## Context

OAA's Mouseion is already an LLM-curated, compounding knowledge substrate (durable records,
provenance, adversarial confidence, lexical + semantic retrieval). What it lacks is a *disciplined
lifecycle* for how knowledge is added, retrieved, and kept healthy over time. Knowledge currently
accretes as records but there is no systematic synthesis-on-ingest, no promotion of good answers back
into the store, and no health check for staleness/contradiction.

Karpathy's LLM-maintained-wiki pattern names this lifecycle precisely: three layers (immutable raw
sources → LLM-owned wiki → human-curated load-bearing schema) and three operations — **ingest**,
**query**, **lint**. The human curates sources and asks questions; the LLM does the synthesis,
cross-referencing, contradiction detection, and bookkeeping.

## Decision

Adopt the pattern and **build it operationally** over the Mouseion knowledge layer as the headline of
Phase 1. Specifically:

1. Treat raw sources as immutable; make only the wiki layer mutable. The schema doc is
   `docs/knowledge.md` (load-bearing — it configures the LLM's behavior).
2. Implement **ingest**: a new source triggers synthesis + cross-referencing + contradiction detection
   across related records, preserving provenance.
3. Implement **query**: retrieve from the wiki, and promote valuable answers into new entries (the
   compounding mechanism).
4. Implement **lint**: periodic health check reporting staleness, orphans, contradictions, and missing
   concepts, with measurable counts feeding `docs/evaluation.md`.

The same discipline governs this repo's own `docs/` tree (sources = code/commits; wiki = docs;
schema = CLAUDE.md + `docs/knowledge.md`).

## Constraints

- **Offline-first:** all three operations must be testable against the deterministic / mock provider;
  no live API calls in CI (per the tech-stack decision).
- **Additive flesh:** build on the existing `KnowledgeBackend` / `VectorStore` / provider seams. Do not
  change shell contracts (`mouseion/contracts.py`, `KnowledgeRecordV0`) without separate approval.
- **Adversarial confidence preserved:** ingest must not introduce self-rated confidence.

## Consequences

- **Positive:** a disciplined, measurable knowledge lifecycle; the docs-tracking system and the runtime
  knowledge system share one mental model; lint gives the wiki health an SLI.
- **Cost:** new operations + tests to build; care needed to keep ingest deterministic for tests.
- **Reversal:** if the operational build proves too heavy, fall back to the pattern as docs-discipline
  only (recorded as a superseding decision-log entry).

## Alternatives considered

- **Reference only** (note the pattern, build nothing) — rejected: doesn't move the knowledge layer
  forward.
- **Governance/docs-discipline only** (no runtime build) — rejected for now as the chosen scope is to
  build it operationally; remains the documented fallback.
</content>
