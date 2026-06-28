# Implementation Roadmap

## Status

| Feature | Branch | Status |
|---------|--------|--------|
| Core architecture (StemCell → Cell → Organ → Body) | main | ✅ Complete |
| Mouseion substrate (in-memory) | main | ✅ Complete |
| Slime mold adaptive network | main | ✅ Complete |
| Evolution engine (fitness, selection, mutation) | main | ✅ Complete |
| ExMorbus medical domain | main | ✅ Complete |
| SLA/SLO/SLI observability layer | main | ✅ Complete |
| LLM-backed agent cognition | feature/llm-cognition | 🔜 Next |
| Persistent Mouseion (SQLite + vector store) | feature/persistent-mouseion | 🔜 Queued |
| Autoresearch self-improvement loop | feature/autoresearch | 🔜 Queued |
| Web dashboard | feature/web-dashboard | 🔜 Queued |
| Multi-process / distributed ecosystem | feature/distributed-ecosystem | 🔜 Queued |

---

## Feature 1 — LLM-Backed Agent Cognition (`feature/llm-cognition`)

### Goal

Convert agents from stochastic template actors into real AI decision-makers.
Each differentiated `Cell` gains the ability to reason about its environment,
query the Mouseion, and produce richly-structured knowledge via an LLM call.
Genome traits bias the system prompt — a high-`curiosity` researcher explores
wider; a low-`risk_tolerance` pharmacologist is more conservative.

### Architecture

```
src/cognition/
├── contracts.py          # Shell: CognitionRequestV0, CognitionResponseV0
├── provider.py           # Shell: AbstractLLMProvider protocol
├── genome_prompt.py      # Genome trait → prompt bias (qualitative language)
├── anthropic_provider.py # Flesh: Anthropic Claude (default)
├── openai_provider.py    # Flesh: OpenAI GPT-4o
└── cognitive_cell.py     # LLM-backed Cell subclass
```

### Design Decisions

1. **MoltBook pattern preserved**: `contracts.py` and `provider.py` are shell.
   `anthropic_provider.py` / `openai_provider.py` are flesh — hot-swappable
   without touching any other module.

2. **Genome → prompt translation**:
   Each of the 8 genome traits maps to qualitative instructions injected into
   the system prompt. Example:
   - `curiosity=0.9` → `"Explore broadly; consider unconventional hypotheses"`
   - `compassion=0.9` → `"Prioritise patient safety above all else"`
   - `risk_tolerance=0.2` → `"Be conservative; cite established evidence"`

3. **Structured output via tool use**:
   LLM responses are forced through a structured tool call so output is always
   a validated `CognitionResponseV0`, not free-form text. This prevents
   hallucination from leaking into the Mouseion knowledge store.

4. **Prompt caching (Anthropic)**:
   The role system prompt + genome bias block is a long, stable prefix.
   Marked `cache_control: {"type": "ephemeral"}` for 5-minute cache reuse.
   Agents in the same role share cached prefix tokens — 90%+ cache hit rate
   expected in a colony.

5. **Lazy invocation**:
   LLM is only called when an agent is making a real decision — not every tick.
   Cognitive agents invoke LLM at most once per tick (configurable) and fall
   back to stochastic behavior when rate-limited or offline.

6. **Injection safety**:
   All Mouseion content passed to LLM is first sanitized by `sanitize_text()`.
   No raw user/external content reaches the model without sanitization.

### Key Files

| File | Purpose |
|------|---------|
| `src/cognition/contracts.py` | `CognitionRequestV0`, `CognitionResponseV0`, `GenomePromptBias` |
| `src/cognition/provider.py` | `AbstractLLMProvider` (Protocol) |
| `src/cognition/genome_prompt.py` | `genome_to_bias(genome, role) → str` |
| `src/cognition/anthropic_provider.py` | `AnthropicProvider(AbstractLLMProvider)` |
| `src/cognition/openai_provider.py` | `OpenAIProvider(AbstractLLMProvider)` |
| `src/cognition/cognitive_cell.py` | `CognitiveCell(Cell)` with LLM step |

### Tests

- Genome → prompt bias mapping (deterministic)
- Provider protocol compliance
- Structured output parsing / validation
- Mock provider for offline testing
- Integration: CognitiveCell in full ecosystem tick loop

---

## Feature 2 — Persistent Mouseion (`feature/persistent-mouseion`)

### Goal

Swap the in-memory Mouseion flesh for a durable backend so the ecosystem's
knowledge survives across runs. Add semantic vector search so agents can
retrieve conceptually-related knowledge (not just tag-indexed).

### Architecture

```
src/mouseion/backends/
├── base.py               # AbstractMouseionBackend protocol (shell)
├── memory_backend.py     # Extracted in-memory logic (current behaviour)
├── sqlite_backend.py     # SQLite flesh (zero-dep durable storage)
└── vector_store.py       # FAISS semantic search wrapper
```

The existing `Mouseion` class gains a `backend: AbstractMouseionBackend`
constructor parameter. Default remains `MemoryBackend()` — zero breaking
changes to existing code and tests.

### Design Decisions

1. **Shell unchanged**: `mouseion/contracts.py` and the `Mouseion` public API
   stay identical. Only the internal storage layer is swapped.

2. **SQLite as default durable flesh**:
   - Zero additional infrastructure
   - WAL mode for concurrent readers
   - FTS5 full-text search on knowledge content
   - Alembic schema migrations

3. **FAISS for semantic search**:
   - In-process (no server)
   - Embeddings via `sentence-transformers` (MiniLM) — offline capable
   - `mouseion.semantic_query(text, k=5)` new API (additive, not breaking)

4. **Qdrant as optional production flesh**:
   - Drop-in replacement for FAISS when deploying at scale
   - Same `VectorStore` protocol interface

### Key Files

| File | Purpose |
|------|---------|
| `src/mouseion/backends/base.py` | `AbstractMouseionBackend` protocol |
| `src/mouseion/backends/memory_backend.py` | Extracted in-memory backend |
| `src/mouseion/backends/sqlite_backend.py` | SQLite backend (WAL + FTS5) |
| `src/mouseion/backends/vector_store.py` | FAISS wrapper + `semantic_query()` |

### Tests

- Backend protocol compliance (run same test suite against each backend)
- SQLite persistence across instantiations
- FTS5 full-text search
- FAISS semantic search returns reasonable neighbours
- Zero breaking changes to existing 160 tests

---

## Feature 3 — Autoresearch Self-Improvement Loop (`feature/autoresearch`)

### Goal

Flesh out `Body._self_improvement_cycle()` into a real autonomous
experimentation system inspired by karpathy/autoresearch. The Body proposes
changes to system parameters, runs fixed-budget experiments, measures the
fitness delta, and commits improvements or rolls back regressions.

### Architecture

```
src/autoresearch/
├── contracts.py          # ExperimentV0, ExperimentResultV0, ImprovementCycleV0
├── proposer.py           # Generates typed experiment proposals
├── runner.py             # Executes fixed-budget experiment ticks
├── evaluator.py          # Before/after FitnessVector comparison
└── integration.py        # Hooks Body._self_improvement_cycle()
```

### Experiment Types

| Type | What Changes | Revert Mechanism |
|------|-------------|-----------------|
| `niche_urgency` | Urgency growth rate of one niche | Restore original value |
| `genome_bias` | Mutation rate / sigma in Mutator | Restore original params |
| `energy_regen` | Resource pool regen rate | Restore original rate |
| `signal_weight` | Signal attenuation factor | Restore original factor |
| `carrying_capacity` | Selector carrying capacity | Restore original value |

### Experiment Loop

```
for each self-improvement cycle (every 20 ticks):
    baseline = FitnessEvaluator.evaluate_population(env)
    proposal = Proposer.propose(baseline, experiment_history)
    checkpoint = Checkpointer.snapshot(env, proposal.target)
    run N=10 ticks with proposal applied
    result = FitnessEvaluator.evaluate_population(env)
    delta = result.overall - baseline.overall
    if delta > IMPROVEMENT_THRESHOLD:
        commit (log to Mouseion, keep change)
    else:
        Checkpointer.restore(checkpoint)
    ImprovementCycleV0 → Mouseion.store_knowledge(topic_tags=["autoresearch"])
```

### Design Decisions

1. **Fixed-budget**: Each experiment runs exactly N ticks (default 10). No
   experiment blocks indefinitely.

2. **Proposal history**: The Proposer reads previous experiment records from
   the Mouseion to avoid repeating failed proposals and to compound successes.

3. **Non-destructive rollback**: The Checkpointer only snapshots the
   parameters being changed — not the full ecosystem state. This is fast
   and avoids deep-copying the knowledge store.

4. **Compassion guard**: Proposals that would reduce `compassion` genome bias
   or `adverse_event_coverage` below thresholds are rejected before running.

### Tests

- Proposer generates valid typed proposals
- Experiment runs without error
- Rollback restores exact original params
- Improvement is committed; regression is reverted
- Compassion guard rejects harmful proposals
- Experiment history is stored in Mouseion

---

## Feature 4 — Web Dashboard (`feature/web-dashboard`)

### Goal

Real-time browser-based visualization of the running ecosystem. Stakeholders
can watch agents differentiate, organs form, and SLOs breach/recover without
reading log lines.

### Architecture

```
src/dashboard/
├── app.py                # FastAPI app + WebSocket broadcaster
├── router.py             # REST routes (/api/state, /api/history, /api/slos)
├── sim_runner.py         # Async simulation runner (wraps Environment.tick())
└── static/
    ├── index.html        # Single-page app shell
    ├── style.css         # Minimal styling
    └── app.js            # WebSocket client + Chart.js visualisations
```

### Views

| Panel | Data Source | Update Rate |
|-------|------------|-------------|
| Agent grid | `env.all_agents()` snapshot | Every tick |
| Role distribution | agent role counts | Every tick |
| Network topology | `SlimeMoldNetwork.summary()` | Every 5 ticks |
| Knowledge growth | `mouseion.knowledge_count()` | Every tick |
| SLO dashboard | `tracker.latest_report()` | Every tick |
| Fitness history | `body._improvement_history` | Every 20 ticks |
| Event timeline | `mouseion.event_history()` | Every tick |

### Design Decisions

1. **No build step**: Vanilla JS + HTMX + Chart.js via CDN. No node_modules,
   no webpack. The dashboard is a static file served by FastAPI.

2. **WebSocket for live data**: FastAPI `WebSocket` endpoint broadcasts a
   compact JSON tick summary to all connected clients. Clients apply delta
   updates rather than full-page refreshes.

3. **REST for history**: Historical data (fitness curves, experiment logs) are
   fetched via regular REST endpoints on demand.

4. **Configurable tick rate**: Dashboard exposes a speed slider (1–100 ticks/s)
   that controls `asyncio.sleep()` between ticks.

5. **Standalone**: Dashboard can run against any ecosystem configuration
   (generic, ExMorbus medical, custom). It reads the SLA from the tracker.

### Tests

- FastAPI routes return valid JSON
- WebSocket broadcasts valid tick payloads
- Sim runner advances the environment correctly
- Static files are served

---

## Feature 5 — Multi-Process / Distributed Ecosystem (`feature/distributed-ecosystem`)

### Goal

Run multiple Environment instances (potentially on separate processes/machines)
sharing a single persistent Mouseion, with inter-Body signal bridges.

### Architecture

```
src/distributed/
├── async_environment.py  # asyncio-native Environment (non-blocking tick)
├── runner.py             # AsyncSimulationRunner (N environments, shared Mouseion)
├── bridge.py             # Inter-Body signal bridge (SYNC signals cross boundaries)
└── coordinator.py        # Top-level orchestration + health monitoring
```

### Design Decisions

1. **asyncio-first**: Each environment runs in its own asyncio `Task`. The
   shared Mouseion backend uses async-safe locking (already thread-safe;
   asyncio wraps synchronously).

2. **Shared Mouseion**: All environments share one `Mouseion` instance (or
   a `SQLiteBackend` Mouseion if they're in separate processes, using WAL mode
   for concurrent access).

3. **Inter-body bridge**: When one Body synthesizes a vision, it emits a
   `SYNC` signal to its local network. The `Bridge` rebroadcasts this signal
   to all other Bodies' networks — enabling cross-ecosystem coordination.

4. **Redis Pub/Sub (optional)**: For truly distributed (separate-machine)
   deployment, replace the bridge with a Redis Pub/Sub adapter. The bridge
   protocol is abstract enough that this is a flesh swap.

5. **Graceful degradation**: If a remote environment disconnects, its local
   agents continue operating with stale cross-body signals. The Bridge
   re-synchronizes when connectivity resumes.

### Tests

- Multiple async environments advance simultaneously
- Knowledge written by one environment is readable by another
- Inter-body SYNC signal propagates correctly
- Disconnection/reconnection cycle
- Coordinator health monitoring

---

## Implementation Order and Rationale

```
1. feature/llm-cognition        (highest-leverage: converts simulation → real AI)
2. feature/persistent-mouseion  (enables LLM to build durable knowledge across runs)
3. feature/autoresearch         (closes self-improvement loop; depends on persistence)
4. feature/web-dashboard        (observability; depends on stable core)
5. feature/distributed-ecosystem (scale; depends on async patterns + persistence)
```

Each feature branch:
- Opens from `main`
- Maintains all existing tests (no regressions)
- Adds its own test suite before merging
- Gets a doc entry in `docs/`
- Is merged to `main` via a clean commit history

---

## Cross-Cutting Concerns

### Security
- All content stored in Mouseion passes through `sanitize_text()` before
  LLM injection (already in place)
- LLM API keys via environment variables only — never hardcoded
- Structured output enforced via tool use — no raw LLM text in knowledge store

### Observability
- SLITracker hooks into every new component
- Each new feature emits typed `EventKind` events to the Mouseion bus
- Dashboard shows all components in a unified view

### Backwards Compatibility
- Shell contracts never change; only version-bump when required
- New features are additive: existing examples and tests continue to run
  without configuration changes
