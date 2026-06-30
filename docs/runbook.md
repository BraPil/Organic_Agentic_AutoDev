# Operational Runbook

Practical procedures for running, debugging, testing, and extending the
Organic Agentic AutoDev ecosystem.

---

## 1. Environment Setup

```bash
# Install with dev + LLM extras
pip install -e ".[dev,llm]"

# Verify install
python -c "from organic_agentic_autodev.mouseion.substrate import Mouseion; print('OK')"
```

### Optional environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Anthropic provider (LLM cognition) | unset → MockProvider |
| `OPENAI_API_KEY` | OpenAI provider (LLM cognition) | unset → MockProvider |
| `OAAD_LLM_PROVIDER` | Force provider: `anthropic` / `openai` / `mock` | `mock` if no key |
| `OAAD_MOUSEION_BACKEND` | `memory` / `sqlite` | `memory` |
| `OAAD_MOUSEION_DB` | SQLite DB path | `mouseion.db` |
| `OAAD_LOG_LEVEL` | Python log level | `INFO` |

> The system runs fully offline with zero keys set — agents fall back to
> stochastic behavior and the in-memory Mouseion.

---

## 2. Running the Ecosystem

### Generic colony

```bash
python examples/basic_stem_cell.py      # single agent lifecycle
python examples/colony_formation.py     # colony differentiation
python examples/organ_specialization.py # organ emergence
```

### Medical (ExMorbus) ecosystem with SLA tracking

```bash
python examples/medical_ecosystem.py
```

Expected output: per-tick summaries, SLI dashboard every 10/30 ticks,
differentiation timeline, organs formed, Body vision, final SLA compliance.

### LLM-backed cognition (when implemented)

```bash
# Offline (deterministic mock)
python examples/cognitive_demo.py

# Live (requires a real key)
ANTHROPIC_API_KEY=sk-... python examples/cognitive_demo.py
```

### Compounding knowledge wiki (Phase 1) + self-improvement (Phase 3)

```bash
python examples/knowledge_wiki_demo.py   # ingest → query → lint over the Mouseion
python examples/autoresearch_demo.py     # propose → test → commit/rollback loop
```

Both run fully offline (deterministic cognition + retrieval). The wiki and the
autoresearch proposer each accept an optional LLM seam (`LLMWikiCognition`,
`LLMProposalCognition`) that activates only when a provider key is present and
falls back to the deterministic path otherwise.

---

## 3. Testing

```bash
pytest                          # full suite (currently 331 tests)
pytest tests/test_mouseion.py   # one module
pytest -k "differentiation"     # by keyword
pytest --cov=organic_agentic_autodev --cov-report=term-missing   # coverage
```

### Test conventions

- All tests must run **offline** and **deterministically** (seed all RNGs).
- LLM tests use `MockProvider` — never make live API calls in the test suite.
- Each new feature adds its own `tests/test_<feature>.py`.
- A merge to `main` requires the full suite green.

---

## 4. Common Operations

### Inspect the Mouseion at runtime

```python
mouseion.summary()                      # resources, niches, knowledge, events
mouseion.resource_summary()             # per-pool stats
list(mouseion.all_knowledge())          # all knowledge records
mouseion.query_knowledge("oncology")    # by tag
mouseion.event_history(EventKind.DIFFERENTIATION_COMPLETED)
```

### Inspect agents / organs / body

```python
[a.snapshot() for a in env.all_agents()]
[o.snapshot() for o in body._organs.values()]
body.snapshot()
```

### Inspect the slime mold network

```python
network.summary()                       # nodes, edges, avg conductance
network.detect_clusters(min_conductance=0.3)   # organ candidates
```

### Inspect SLA compliance

```python
print(tracker.dashboard_string())       # ASCII dashboard
tracker.compliance_summary()            # structured compliance dict
tracker.slo_status("slo_knowledge_confidence_floor")
```

### Drive the knowledge wiki (Phase 1)

```python
from organic_agentic_autodev.knowledge_wiki import KnowledgeWiki, VectorRetriever
wiki = KnowledgeWiki()                       # default lexical retrieval
wiki = KnowledgeWiki(retriever=VectorRetriever())  # cosine over HashingEmbedder
wiki.ingest("topic: Genome\nEncodes eight traits.\ncount: 8")
wiki.query("how many traits?")               # grounded answer is promoted (wiki:answer)
wiki.lint()                                  # orphans / dangling / missing / contradictions / stubs
```

### Inspect knowledge-wiki health as SLIs (Phase 2)

```python
from organic_agentic_autodev.observability import WikiHealthMonitor
monitor = WikiHealthMonitor(wiki, probe_questions=["how many traits?"])
print(monitor.dashboard_string())            # link integrity / orphan rate / contradictions / grounding
monitor.evaluate()["sla_compliant"]
```

### Enable LLM-backed autoresearch proposals (Phase 3)

```python
from organic_agentic_autodev.autoresearch import Proposer, LLMProposalCognition
# Cognition is advisory (order + increase/decrease + rationale); bounds and the
# compassion guard stay in the Proposer. Falls back to heuristic with no key.
proposer = Proposer(selector=sel, mutator=mut, cognition=LLMProposalCognition())
```

---

## 5. Debugging Guide

| Symptom | Likely cause | Check |
|---------|-------------|-------|
| No agents differentiate | Niche urgency too low or genome threshold too high | `env.open_niches()`, genome `differentiation_threshold` |
| All agents die quickly | Energy pool exhausted | `mouseion.resource_level(ResourceKind.ENERGY)` |
| No organs form | Conductance never reaches threshold | `network.summary()["avg_conductance"]` |
| SLO always INSUFFICIENT_DATA | `min_sample_size` not met | record count / agent count |
| P1 SLO breach spam | Safety roles not differentiating | count GUARDIAN/PHARMACOLOGIST agents |
| LLM calls fail | Missing/invalid key | `echo $ANTHROPIC_API_KEY`; falls back to mock |

### Enable verbose logging

```python
import logging
logging.getLogger("stem_cell").setLevel(logging.DEBUG)
logging.getLogger("cell").setLevel(logging.DEBUG)
logging.getLogger("observability.tracker").setLevel(logging.DEBUG)
```

---

## 6. Tuning Knobs

| Parameter | File | Effect |
|-----------|------|--------|
| `BASELINE_ENERGY_COST` | `core/stem_cell.py` | Cost of living per tick |
| `RESOURCE_DRAW_AMOUNT` | `core/stem_cell.py` | Energy gained per tick |
| `differentiation_threshold` | `core/genome.py` | Signal needed to specialise |
| `EXPLORE_PROB` | `slime_mold/pathfinder.py` | Rate of new connections |
| `DECAY_RATE` | `slime_mold/pathfinder.py` | How fast unused paths atrophy |
| `MIN_ORGAN_SIZE` / `MAX_ORGAN_SIZE` | `organisms/organ.py` | Organ size bounds |
| `carrying_capacity` | `evolution/selector.py` | Max sustainable population |
| `resource_regen_rate` | `core/environment.py` | Resource recovery rate |

---

## 7. Release / Branch Workflow

```bash
# Each feature gets its own branch off main
git checkout main && git pull
git checkout -b feature/<name>

# Develop, keeping all existing tests green
pytest

# Merge back when complete
git checkout main
git merge --no-ff feature/<name>
git push origin main
```

Rules:
- Never commit secrets (API keys live only in env vars).
- The full test suite must pass before merge.
- Shell contracts (`*/contracts.py`, `genome.py`, `signal.py`) only change
  with a version bump and a documented migration.

---

## 8. Incident Response

### "The ecosystem collapsed (all agents dead)"
1. Check energy headroom: `tracker.slo_status("slo_energy_headroom")`
2. If energy pool is depleted, raise `resource_regen_rate` or initial energy.
3. If selection pressure is too harsh, lower `Selector.selection_strength`.

### "P1 patient-safety SLO breached" (medical ecosystem)
1. `adverse_event_coverage` breach → too few GUARDIAN/PHARMACOLOGIST cells.
   Raise the urgency of safety niches in `domain/exmorbus/niches.py`.
2. `knowledge_confidence_floor` breach → low-confidence records dominating.
   Review which agents author low-confidence knowledge.

### "LLM cognition is non-deterministic in tests"
- Tests must use `MockProvider`. If a live provider leaked into a test,
  set `OAAD_LLM_PROVIDER=mock` and assert the provider type in the fixture.
