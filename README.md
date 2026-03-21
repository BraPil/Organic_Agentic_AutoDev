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
src/
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
└── utils/
    └── helpers.py        # Shared utilities, sanitization, logging
examples/
├── basic_stem_cell.py    # Demonstrate a single StemCell lifecycle
├── colony_formation.py   # Watch a colony form and differentiate
└── organ_specialization.py  # Trace organ emergence from cell clusters
tests/
docs/
├── architecture.md
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
- [ ] LLM-backed agent cognition (OpenAI / Anthropic integration)
- [ ] Persistent Mouseion (vector store + SQLite backend)
- [ ] Multi-process / distributed ecosystem
- [ ] Web dashboard for observing emergent behavior
- [ ] Integration with autoresearch for autonomous experimentation
- [ ] ExMorbus domain specialization modules

---

## Status

**Alpha proof of concept.** The architecture is fully specified and the core mechanics are implemented as pure Python (no LLM calls required to explore the dynamics). LLM integration is an optional layer on top of the working simulation.

---

*"The most robust systems in nature are not designed — they grow."*
