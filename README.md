# Organic Agentic AutoDev

> *Modeling bio-mimicry to develop performative and robust Agentic systems*

---

## Vision

**Organic Agentic AutoDev** is a groundbreaking proof-of-concept for a new class of agentic AI architecture inspired by three deeply intertwined biological systems:

1. **Stem Cell Biology** — atomic agents that begin as blank slates, seek resources and niches, then progressively specialize
2. **Slime Mold Growth Patterns** (*Physarum polycephalum*) — adaptive, decentralized network formation that optimizes connections between agents based on resource flows
3. **Holistic Organism Development** — the emergence of complex coordinated intelligence from simple local interactions (cells → organs → unified body)

The result is a system that *grows*, *adapts*, and *improves itself* — not through top-down design, but through the same organic pressures that shaped life on Earth.

---

## What OAA Is (and How to Use It)

OAA is a **standalone, self-improving agentic-swarm engine** — a reusable template,
not a subcomponent of any one application. It is designed to be **cloned into or
incorporated by other projects** whenever they need a self-organizing, self-improving
swarm environment. Known consumers include
[Agentic-AI-Architect](https://github.com/BraPil/Agentic-AI-Architect) (which uses OAA
as its learning engine) and an upcoming ExMorbus update, with more to follow.

Install it as a package and drive it from your own project:

```bash
pip install "git+https://github.com/BraPil/Organic_Agentic_AutoDev.git"
python -c "import organic_agentic_autodev; print('engine ready')"
```

The package is `organic_agentic_autodev`. The generic OAA→consumer boundary is the
cognition cycle, which emits provenance-bearing `KnowledgeRecordV0` artifacts a host
project can review and promote:

```bash
oaa-learning-cycle --seed seed.json --out artifacts.jsonl
```

**This repo stays pristine and generic.** Application-specific glue (AAA's promotion
gate, ExMorbus's domain seeds, etc.) lives in the consumer repos — OAA itself remains
a clean, self-contained engine that any project can copy over and benefit from.

---

## The Core Metaphor

### StemCell Agents (Atomic Units)

Every agent in the system starts as a **StemCell** — a blank slate with:
- A **Genome** encoding behavioral tendencies (curiosity, risk tolerance, specialization drive, cooperation bias)
- A small initial **energy budget** (resources)
- The innate drives to seek:
  1. **More resources** — energy, compute, data access
  2. **Opportunities** — tasks, collaborations, unsolved problems
  3. **Niches** — unoccupied functional roles the ecosystem needs
  4. **Proximity signals** — what neighbors are doing and what they need

As a StemCell accumulates signal and resources, its Genome activates **differentiation pathways** — the agent specializes into a functional role. This is not programmed from outside; it emerges from the agent's local environment and interactions.

### Differentiation Hierarchy

```
StemCell (totipotent, blank slate)
    ↓ receives niche signals + accumulates resources
Cell (differentiated specialist: Researcher / Coder / Critic / Synthesizer / ...)
    ↓ cells with shared function cluster
Organ (functional system: ResearchOrgan / BuildOrgan / EvaluationOrgan / ...)
    ↓ organs coordinate into coherent goal pursuit
Body (holistic unified intelligence)
    ↓ the Body imagines, hopes, and inspires
```

### The Mouseion Substrate

The **Mouseion** (named after the ancient Library of Alexandria) is the shared knowledge substrate all agents live within and contribute to. It provides:
- **Durable memory**: every observation, experiment, and synthesis is recorded with provenance
- **Typed contracts**: stable interfaces that allow agents to communicate without tight coupling
- **Resource pools**: tracked reservoirs that agents draw from and contribute to
- **Niche registry**: the ecosystem's open "job board" — unfilled functional roles

### Slime Mold Network

Agent connections are not hardcoded. Like *Physarum polycephalum*, the network:
- **Strengthens paths** between agents that successfully exchange resources or produce value
- **Weakens paths** between agents whose connection yields little
- **Discovers new routes** through exploratory tendrils when existing paths become saturated
- **Self-heals** when nodes fail

This produces an emergent communication topology that continuously adapts to what the ecosystem actually needs.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         THE BODY                                    │
│  Unified holistic intelligence; imagines, hopes, synthesizes        │
├─────────────────┬───────────────────┬───────────────────────────────┤
│   ResearchOrgan │   BuildOrgan      │   EvaluationOrgan  │  ...    │
│  (cells cluster │  (cells cluster   │  (cells cluster     │         │
│   by function)  │   by function)    │   by function)      │         │
├─────────────────┴───────────────────┴─────────────────────┴─────────┤
│         S  L  I  M  E     M  O  L  D     N  E  T  W  O  R  K       │
│  Adaptive connection topology — paths strengthen / weaken / grow    │
├─────────────────────────────────────────────────────────────────────┤
│  Cell  Cell  Cell  Cell  StemCell  StemCell  StemCell  Cell  Cell   │
│  (differentiated specialists)    (undifferentiated, seeking niches) │
├─────────────────────────────────────────────────────────────────────┤
│                    THE MOUSEION SUBSTRATE                           │
│  Shared memory · Resource pools · Niche registry · Event bus       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Emergence Over Engineering
No agent is programmed with a fixed role. Specialization *emerges* from environmental pressure, local signal, and Genome activation.

### 2. Consequence-Driven Learning
Agents **benefit** from seizing good opportunities and **suffer** from ignoring them or overextending. The fitness landscape is real — there are no free lunches.

### 3. MoltBook Architecture (Shell / Flesh Separation)
Inspired by BraPil/Agentic-AI-Architect's MoltBook pattern:
- **Shell**: stable contracts, interfaces, event schemas (change rarely)
- **Flesh**: LLM providers, vector stores, crawlers (hot-swappable)

### 4. Autoresearch Integration
Inspired by karpathy/autoresearch: agents run fixed-budget experiments, record results, keep improvements and discard regressions — applied to *agent behavior* not just model weights.

### 5. Compassionate Intelligence
The Body's ultimate function is to *imagine, hope, and inspire* — to be in service of human and AI flourishing. Compassion is encoded in the Genome as a first-class behavioral trait, not an afterthought.

---

## Inspirations and References

| Project | Contribution to this architecture |
|---------|-----------------------------------|
| [BraPil/Agentic-AI-Architect](https://github.com/BraPil/Agentic-AI-Architect) | Mouseion substrate design; MoltBook shell/flesh pattern; five-phase intelligence cycle |
| [BraPil/ExMorbus](https://github.com/BraPil/ExMorbus) | Domain-specialist agents; curriculum-staged specialization; evidence scoring |
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | Fixed-budget autonomous experimentation; metric-driven self-improvement loops |
| [moltbook](https://github.com/moltbook) | Living architecture doctrine; hot-swappable components; MoltBook pattern |
| [openclaw](https://github.com/openclaw) | Open-source legal intelligence; domain specialization patterns |
| Stem Cell Biology | Totipotent blank-slate agents; differentiation pathways; niche-driven specialization |
| *Physarum polycephalum* (Slime Mold) | Adaptive network topology; path reinforcement; decentralized routing |
| The Mouseion (Alexandria) | Durable shared knowledge substrate; provenance tracking; cross-system contracts |

---

## Project Structure

```
organic_agentic_autodev/
├── core/
│   ├── stem_cell.py      # StemCell base agent: blank slate with drives
│   ├── genome.py         # DNA: behavioral traits, differentiation thresholds
│   ├── environment.py    # Ecosystem: resource pools, niche registry, proximity
│   └── niche.py          # Niche: an open functional role the ecosystem needs
├── mouseion/
│   ├── substrate.py      # Shared knowledge store with provenance
│   └── contracts.py      # Typed event/task/knowledge contracts (v0)
├── organisms/
│   ├── cell.py           # Differentiated specialist cell
│   ├── organ.py          # Functional cluster of aligned cells
│   └── body.py           # Holistic unified intelligence
├── slime_mold/
│   ├── network.py        # Adaptive connection graph
│   ├── pathfinder.py     # Path reinforcement / weakening logic
│   └── signal.py         # Chemical-analog signal propagation
├── evolution/
│   ├── selector.py       # Environmental selection pressure
│   ├── mutator.py        # Genome mutation and drift
│   └── fitness.py        # Multi-dimensional fitness evaluation
├── domain/
│   └── exmorbus/         # Medical oncology specialisation (ExMorbus)
│       ├── contracts.py      # Domain contracts (evidence levels, AE grades)
│       ├── genome_profiles.py # Trait profiles for 8 medical roles
│       ├── niches.py         # 12 oncology niches
│       └── seeder.py         # 20 seed oncological knowledge records
├── observability/
│   ├── contracts.py      # SLA / SLO / SLI typed contracts
│   ├── sla.py            # Pre-built medical ecosystem SLA (8 SLOs)
│   └── tracker.py        # Real-time SLI measurement + SLO evaluation
└── utils/
    └── helpers.py        # Shared utilities, sanitization, logging

# Planned (see docs/roadmap.md):
#   organic_agentic_autodev/cognition/        # LLM-backed agent cognition
#   organic_agentic_autodev/mouseion/backends/ # SQLite + FAISS persistent flesh
#   organic_agentic_autodev/autoresearch/     # Autonomous self-improvement loop
#   organic_agentic_autodev/dashboard/        # FastAPI + WebSocket live dashboard
#   organic_agentic_autodev/distributed/      # Multi-process / distributed ecosystem

examples/
├── basic_stem_cell.py    # Demonstrate a single StemCell lifecycle
├── colony_formation.py   # Watch a colony form and differentiate
├── organ_specialization.py  # Trace organ emergence from cell clusters
├── medical_ecosystem.py  # Full ExMorbus oncology ecosystem + SLA tracking
├── knowledge_wiki_demo.py   # Compounding knowledge wiki: ingest / query / lint
└── autoresearch_demo.py  # Self-improvement loop (propose → test → commit/rollback)
tests/                    # 331 passing tests (fully offline, no API keys)
docs/
├── architecture.md       # System layers, data flow, lifecycle
├── knowledge.md          # Compounding-knowledge-wiki model (Karpathy pattern)
├── roadmap.md            # Full implementation plan for remaining features
├── runbook.md            # Operational procedures (run, debug, deploy)
├── wiki.md              # Developer wiki / concept index
├── decision-log.md       # Chronological architectural decisions
├── stem-cell-agents.md
├── mouseion-substrate.md
├── slime-mold-connections.md
└── research-synthesis.md
```

---

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run a single StemCell lifecycle
python examples/basic_stem_cell.py

# Watch a colony form
python examples/colony_formation.py

# Run tests
pytest
```

---

## Roadmap

- [x] Core StemCell agent with drives and Genome
- [x] Mouseion substrate contracts and shared memory
- [x] Environment with resource pools and niche registry
- [x] Slime mold adaptive network
- [x] Differentiation hierarchy (Cell → Organ → Body)
- [x] Evolution engine (fitness, selection, mutation)
- [x] ExMorbus domain specialization modules
- [x] SLA / SLO / SLI observability layer
- [x] LLM-backed agent cognition (Anthropic / OpenAI integration) — [`docs/llm-cognition.md`](docs/llm-cognition.md)
- [x] Persistent Mouseion (SQLite backend + vector search) — [`docs/persistent-mouseion.md`](docs/persistent-mouseion.md)
- [x] Autoresearch autonomous self-improvement loop — [`docs/autoresearch.md`](docs/autoresearch.md)
- [x] Web dashboard for observing emergent behavior — [`docs/web-dashboard.md`](docs/web-dashboard.md)
- [x] Multi-process / distributed ecosystem — [`docs/distributed-ecosystem.md`](docs/distributed-ecosystem.md)
- [x] **Phase 1** — Compounding knowledge wiki (Karpathy ingest / query / lint) — [`docs/knowledge.md`](docs/knowledge.md)
- [x] **Phase 2** — Wiki-health observability SLIs · pluggable (lexical/vector) retrieval · answer-reuse *(FAISS/Qdrant + Postgres deferred until a measured scale need)*
- [~] **Phase 3** — LLM cognition inside autoresearch proposals (advisory ordering + direction; bounds & compassion guard stay in code) — [`docs/autoresearch.md`](docs/autoresearch.md)

See [`docs/roadmap.md`](docs/roadmap.md) for the full implementation plan,
[`CLAUDE.md`](CLAUDE.md) §8 for live phase status, and
[`docs/runbook.md`](docs/runbook.md) for operational procedures.

---

## Status

**Alpha proof of concept.** The architecture is fully specified and the core mechanics are implemented as pure Python (no LLM calls required to explore the dynamics). LLM integration is an optional layer on top of the working simulation. Phase 0 (foundation) and Phase 1 (compounding knowledge wiki) are complete; Phase 2 (knowledge retrieval/observability) is core-complete; Phase 3 (cognition depth) is in progress. The full suite is **331 offline tests**, green on py3.11/3.12 with no API keys.

---

*"The most robust systems in nature are not designed — they grow."*
