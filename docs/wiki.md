# Developer Wiki

A concept index and navigation hub for the Organic Agentic AutoDev codebase.
Start here when onboarding or looking for "where does X live."

---

## Documentation Map

| Doc | Read it for |
|-----|-------------|
| [README](../README.md) | Vision, metaphor, quick start |
| [architecture.md](architecture.md) | System layers, data flow, lifecycle, future layers |
| [roadmap.md](roadmap.md) | Full implementation plan for remaining features |
| [runbook.md](runbook.md) | How to run, debug, tune, deploy |
| [llm-cognition.md](llm-cognition.md) | LLM-backed agent cognition (genome → prompt) |
| [persistent-mouseion.md](persistent-mouseion.md) | SQLite backend + semantic vector search |
| [autoresearch.md](autoresearch.md) | Autonomous self-improvement loop |
| [web-dashboard.md](web-dashboard.md) | Live observability dashboard |
| [distributed-ecosystem.md](distributed-ecosystem.md) | Multi-node / distributed ecosystem |
| [stem-cell-agents.md](stem-cell-agents.md) | Drives, differentiation, reproduction |
| [mouseion-substrate.md](mouseion-substrate.md) | Shared memory, contracts, resource pools |
| [slime-mold-connections.md](slime-mold-connections.md) | Adaptive network, conductance, clustering |
| [research-synthesis.md](research-synthesis.md) | Inspirations and how they were synthesised |

---

## Glossary

| Term | Meaning | Code |
|------|---------|------|
| **StemCell** | Totipotent blank-slate agent; no fixed role | `core/stem_cell.py` |
| **Genome** | 8 behavioral traits ∈ [0,1] biasing decisions | `core/genome.py` |
| **Differentiation** | Irreversible commitment to a role when signal > threshold | `StemCell._attempt_differentiation` |
| **Cell** | A differentiated StemCell with role-specific behavior | `organisms/cell.py` |
| **Organ** | Emergent cluster of 2–12 compatible Cells | `organisms/organ.py` |
| **Body** | Holistic intelligence synthesising organ outputs | `organisms/body.py` |
| **Mouseion** | Shared knowledge substrate (memory + niches + resources + events) | `mouseion/substrate.py` |
| **Niche** | An open functional role the ecosystem needs filled | `core/niche.py` |
| **Slime Mold Network** | Adaptive comms topology; conductance reinforces with use | `slime_mold/network.py` |
| **Signal** | Chemical-analog message (FOOD/DANGER/OPPORTUNITY/KNOWLEDGE/SYNC) | `slime_mold/signal.py` |
| **Conductance** | Edge strength [0.01–1.0]; grows on use, decays passively | `slime_mold/pathfinder.py` |
| **FitnessVector** | 6-dimensional fitness evaluation | `evolution/fitness.py` |
| **Niche urgency** | Pressure that grows while a niche is unfilled | `core/niche.py` |
| **ExMorbus** | Medical oncology domain specialisation | `domain/exmorbus/` |
| **SLI / SLO / SLA** | Observability: indicator / objective / agreement | `observability/` |
| **MoltBook pattern** | Shell (stable contracts) vs flesh (swappable impl) | architecture-wide |

---

## "Where do I…" Quick Reference

| I want to… | Go to |
|------------|-------|
| Add a new agent role | `mouseion/contracts.py` (`AgentRole`), `core/niche.py` (`ROLE_GENOME_WEIGHTS`), `organisms/cell.py` (`COMPATIBLE_ROLES` + action method) |
| Change how agents specialise | `core/stem_cell.py` (`_evaluate_opportunities`, `_attempt_differentiation`) |
| Add a knowledge type | `mouseion/store_knowledge()` call sites; tags drive retrieval |
| Add a resource type | `mouseion/contracts.py` (`ResourceKind`), `substrate.py` defaults |
| Add a new event | `mouseion/contracts.py` (`EventKind`), emit via `mouseion.emit()` |
| Tune the network | `slime_mold/pathfinder.py` constants |
| Add an SLO | `observability/sla.py`, add an SLI measure in `tracker.py` |
| Seed domain knowledge | `domain/exmorbus/seeder.py` (`_SEED_ENTRIES`) |
| Change fitness weights | `evolution/fitness.py` (`FitnessVector.weights`) |

---

## The Shell / Flesh Boundary (MoltBook)

**Shell — change rarely, version-bump when you do:**
- `mouseion/contracts.py`
- `core/genome.py`
- `slime_mold/signal.py`
- `observability/contracts.py`
- `domain/exmorbus/contracts.py`
- All `__init__.py` public APIs

**Flesh — swap freely:**
- `mouseion/substrate.py` (→ SQLite, Postgres)
- `slime_mold/pathfinder.py` (→ custom graph)
- LLM providers (→ Anthropic, OpenAI, local)
- Vector stores (→ FAISS, Qdrant)

When adding a feature, ask: *am I changing shell or adding flesh?* Prefer flesh.

---

## Invariants (do not break)

1. **Sanitisation**: every string entering the Mouseion passes `sanitize_text()`.
2. **Determinism**: seed all RNGs; tests must be reproducible and offline.
3. **Conservation**: resource pools conserve — every `draw` decrements, every
   `deposit` increments.
4. **Irreversibility**: differentiation (`_differentiated = True`) is permanent.
5. **Compassion as first-class**: `compassion` is a genome trait and a fitness
   dimension — never demote it to a post-hoc filter.
6. **Local information only**: agents act on genome + proximity + Mouseion
   queries; no global omniscient state.

---

## Component Interaction Diagram

```
              ┌──────────────┐
              │     Body     │  vision, self-improvement
              └──────┬───────┘
                     │ registers / reports
              ┌──────▼───────┐
              │    Organ     │  shared energy, synthesis
              └──────┬───────┘
                     │ clusters from
   ┌─────────────────▼──────────────────┐
   │   Cell ←→ SlimeMoldNetwork ←→ Cell  │  signals, conductance
   └─────────────────┬──────────────────┘
                     │ differentiates from
              ┌──────▼───────┐
              │   StemCell   │  drives, genome
              └──────┬───────┘
                     │ lives in
   ┌─────────────────▼──────────────────┐
   │  Environment  +  Mouseion substrate │  resources, niches, knowledge, events
   └─────────────────┬──────────────────┘
                     │ observed by
              ┌──────▼───────┐
              │  SLITracker  │  SLI/SLO/SLA compliance
              └──────────────┘
```
