# Security

Threat model, injection defense, and secret hygiene. Security is Constitution rank 7 —
"sanitize, authenticate, rate-limit from day one."

## Threat model (what we defend against)

OAA ingests knowledge from sources that may ultimately reach an LLM prompt (cognition cells, the
bridge) and a shared knowledge store consumed by other projects. The primary threats:

1. **Prompt injection** via knowledge content — a source crafted to hijack a cell's or critic's
   reasoning, or to poison records that downstream consumers (AAA, ExMorbus) trust.
2. **Knowledge poisoning** — low-quality or adversarial records inflating confidence to clear the
   0.70 consumer gate.
3. **Secret leakage** — API keys committed or logged.

## Injection defense

- **Sanitize everything entering the Mouseion or any prompt** via `sanitize_text()`. This is invariant
  #1 in `docs/wiki.md` and an anti-pattern to bypass ("this source is internal" is not an exception).
- Knowledge confidence is **adversarial** (mean critic score), which structurally resists self-asserted
  poisoning — a poisoned finding still has to survive independent critics.
- The Phase 1 wiki `ingest` operation treats raw sources as **immutable, untrusted ground truth**; only
  the LLM-owned wiki layer is mutable, and contradiction detection runs on update.

## Secret hygiene

- No API keys, tokens, or credentials in the repo, in logs, or in committed test fixtures
  (CLAUDE.md §3 — committing secrets is a **Block** action).
- LLM providers read keys from the environment at runtime; tests never require them (offline by
  default). `MockProvider` / `DeterministicCognition` back all test paths.
- `structlog` events must not interpolate secrets.

## Authentication / rate-limiting

- The dashboard (`dashboard/app.py`) is a read-only local observer; if exposed beyond localhost it
  needs an auth layer and rate limiting first (not yet built — note it before any public deploy).
- External LLM/API calls (optional flesh) should be rate-limited and use a standard client/session;
  no bare unbounded request loops.

## Open items

- Public-facing dashboard hardening (auth + rate limit) — deferred until Phase 4 deploy hardening.
- A sanitization conformance test that proves every Mouseion entry path routes through `sanitize_text()`.
</content>
