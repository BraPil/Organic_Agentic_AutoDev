# Evaluation

How OAA measures whether it works — for both the deterministic engine and the LLM-backed paths.

## Two evaluation regimes

OAA runs offline by default, so evaluation splits cleanly:

1. **Deterministic engine** — seeded RNGs make every ecosystem run reproducible. Tests assert exact
   or bounded outcomes (resource conservation, differentiation irreversibility, cluster formation,
   fitness ordering). This is the bulk of the 326-test suite.
2. **LLM-backed paths** (cognition cells, the Researcher→Critic→Synthesizer bridge) — evaluated
   against a **deterministic / mock provider** in tests. Live model behavior is validated manually,
   out of band, and the result recorded in `docs/discovery-log.md` (never in CI).

## Observability as evaluation (SLI/SLO/SLA)

The `observability/` layer is the primary runtime eval mechanism. `SLITracker` subscribes to Mouseion
events and measures 8 SLIs per tick against an SLA with priority tiers:

- **P1** (hard): adverse-event coverage ≥ 100%, knowledge-confidence-mean ≥ 0.70 → DANGER on breach.
- **P2**: niche-fill-rate ≥ 80%, guideline-adherence ≥ 90%, knowledge-growth ≥ 2/10t, consensus ≥ 60%.
- **P3**: organ-viability ≥ 50%, energy-headroom ≥ 20%.

"If it isn't logged and measurable, it doesn't exist" (Constitution rank 1) means a new capability
should land with an SLI or assertion that proves it is working.

### Knowledge-wiki health SLA (Phase 2, slice C)

The compounding wiki's health is its own measurable surface. `WikiHealthMonitor`
(`observability/wiki_health.py`) is a **passive observer** — it reads a `KnowledgeWiki`, runs a single
`lint()` pass plus optional probe `query()`s, and evaluates four SLIs against `build_wiki_health_sla()`,
reusing the same shell contracts as `SLITracker` (it writes nothing back; probe queries use
`promote=False`):

- **`wiki_link_integrity`** (P2, GTE 1.0) — fraction of cross-references that resolve (collapses `lint`'s
  dangling-links + missing-concepts into one defect signal).
- **`wiki_orphan_rate`** (P3, LTE 0.0) — fraction of pages disconnected from the link graph.
- **`wiki_contradiction_count`** (P2, LTE 0.0, at-risk ≤ 2) — unresolved flag-and-keep conflicts.
- **`query_grounding_rate`** (P2, GTE 0.80) — fraction of probe questions that retrieve ≥1 page; with
  no probes supplied it reports INSUFFICIENT_DATA rather than guessing. This is the **baseline a future
  vector-retrieval upgrade (Phase 2 slice A) is judged against** — instrument before optimizing
  (Constitution rank 2).

`lint`'s **stubs** are reported but intentionally *not* gated by an SLO — an under-developed page is an
advisory nudge, not a health breach. Determinism holds: `lint` and lexical retrieval are reproducible,
so re-evaluating an unchanged wiki yields identical SLI values (offline, no API key).

## Confidence & uncertainty policy

- Knowledge-record confidence is **adversarial**: the mean of independent critic scores, never
  self-rated (decision-log 2026-06-28). AAA consumes records gated at confidence ≥ 0.70.
- When a result depends on a live model, state the uncertainty and the validation method; do not
  assert a live-model outcome from a mock-tested path.

## Phase 1 (knowledge wiki) eval targets

Per the Karpathy pattern, the wiki's health is itself measurable — and `lint` is how we measure it:
orphan pages, detected contradictions, missing-concept/dangling-link gaps. As of Phase 2 slice C these
are **wired into the SLI/SLO framework** via the wiki-health SLA above (`WikiHealthMonitor`), evaluated
offline via the deterministic provider. Wall-clock staleness remains deferred — it needs a tick/version
baseline and would make `lint` non-deterministic.
</content>
