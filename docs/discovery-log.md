# Discovery Log

Important findings that affect future work — gotchas, non-obvious behaviors, and constraints
discovered during development. If a discovery changes how something *must* be built, record it here
so it isn't rediscovered the hard way.

Format: `### YYYY-MM-DD — <title>` · what was found · why it matters.

---

### 2026-06-28 — FastAPI WebSocket breaks under `from __future__ import annotations`

`organic_agentic_autodev/dashboard/app.py` deliberately omits `from __future__ import annotations`.
With it enabled, FastAPI's WebSocket parameter injection fails because the stringized annotations
can't be resolved under the module's function-local imports. **Do not add the future-annotations
import to `app.py`.** Other modules may use it freely.

---

### 2026-06-28 — `httpx` must be declared for dashboard tests

Starlette's `TestClient` needs `httpx` as its transport, but starlette only lists it optionally.
Without an explicit `httpx>=0.27` in the `[dev]` extra, the 5 dashboard route/websocket tests error
on a fresh install. It is declared in `pyproject` `[dev]` for reproducible CI.

---

### 2026-06-28 — Cognition bridge clears AAA's 0.70 gate with mean-critic scoring

A live 3-Researcher / 2-Critic / 1-Synthesizer cycle produced synthesis confidence 0.80 using the
mean-of-critic-scores method — comfortably above AAA's 0.70 acceptance gate. This validates the
adversarial scoring choice (see decision-log 2026-06-28).

---

### 2026-06-28 — Optional engines were pip-installed during validation but are NOT required

`anthropic`, `fastapi`, and `uvicorn` were installed into the dev environment while validating the
LLM, dashboard, and distributed features. They are optional extras (`[llm]`, `[dashboard]`), not core
deps — the 251-test suite stays green without them. Don't let a green local run mask a missing extra;
CI installs `[dev,dashboard]` explicitly.

---

### 2026-06-30 — `HashingEmbedder` cosine noise rivals weak signal → grounding thresholds are embedder-dependent

Building `VectorRetriever` (Phase 2 slice A) over the existing offline `HashingEmbedder`, measured cosine
on a 2-page corpus: a genuine weak match (`"how many traits does the genome encode?"` → genome page) scored
**0.267**, while a fully *disjoint* query (`"xylophone quasar marimba"` → pathfinder page) spiked to **0.253**
purely from feature-hash bucket collisions. The two bands nearly touch.

**Consequence:** with a bag-of-words feature-hashing embedder there is no clean absolute cosine threshold
separating noise from weak signal on short queries. `VectorRetriever.min_similarity` defaults to a
**conservative 0.3** (favor precision — never promote a noise-grounded answer into the durable store — over
recall). A real semantic embedder (`SentenceTransformerEmbedder`) separates the bands far better and should
use a lower threshold. Tests must not depend on the razor-thin noise/signal boundary: assert on clearly-strong
(≥0.4) vs clearly-absent (≤0.25) cases, or on the threshold *mechanism* (a 0.99 cutoff ungrounds everything).
This is why `HashingEmbedder`-vector retrieval is a demonstrable *seam*, not a retrieval-quality upgrade —
the quality win needs real embeddings.
</content>
