# Evaluation

How OAA measures whether it works — for both the deterministic engine and the LLM-backed paths.

## Two evaluation regimes

OAA runs offline by default, so evaluation splits cleanly:

1. **Deterministic engine** — seeded RNGs make every ecosystem run reproducible. Tests assert exact
   or bounded outcomes (resource conservation, differentiation irreversibility, cluster formation,
   fitness ordering). This is the bulk of the 290-test suite.
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

## Confidence & uncertainty policy

- Knowledge-record confidence is **adversarial**: the mean of independent critic scores, never
  self-rated (decision-log 2026-06-28). AAA consumes records gated at confidence ≥ 0.70.
- When a result depends on a live model, state the uncertainty and the validation method; do not
  assert a live-model outcome from a mock-tested path.

## Phase 1 (knowledge wiki) eval targets

Per the Karpathy pattern, the wiki's health is itself measurable — and `lint` is how we measure it:
staleness count, orphan pages, detected contradictions, missing-concept gaps. These become SLIs/
assertions as the ingest/query/lint operations land. Evaluate offline via the deterministic provider.
</content>
