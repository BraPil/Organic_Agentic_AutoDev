# Architecture Deep Dive

## System Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4: THE BODY                                                  │
│  • Holistic unified intelligence                                    │
│  • Synthesises all organ outputs into a unified vision              │
│  • "Imagines, hopes, and inspires" — compassionate intelligence     │
│  • Self-improvement cycles (metric-driven; autoresearch-style)      │
│  • Sets high-level goals that flow down to Organs                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ registers organs, receives reports
┌──────────────────────────▼──────────────────────────────────────────┐
│  LAYER 3: ORGANS                                                    │
│  • Functional clusters of aligned Cells                             │
│  • Emerge from slime mold cluster detection                         │
│  • Collective energy management (shared pool, levy system)          │
│  • Produce higher-quality synthesised knowledge records             │
│  • ResearchOrgan / BuildOrgan / EvaluationOrgan / ...               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ cells step, cluster by compatible roles
┌──────────────────────────▼──────────────────────────────────────────┐
│  LAYER 2: CELLS                                                     │
│  • Differentiated StemCells: committed to one AgentRole             │
│  • Role-specific step behaviour (research, code, critique, ...)     │
│  • Contribute to Mouseion knowledge store                           │
│  • Emit and respond to slime mold signals                           │
│  • Seek cluster partners via proximity + role compatibility         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ emerges from StemCell differentiation
┌──────────────────────────▼──────────────────────────────────────────┐
│  LAYER 1: STEM CELLS (ATOMIC AGENTS)                                │
│  • Blank slate: no role, no fixed function                          │
│  • Genome encodes behavioral tendencies (8 traits)                  │
│  • Drives: seek resources → scan proximity → evaluate niches        │
│  • Accumulate differentiation signal from niche broadcasts          │
│  • Differentiate when signal exceeds genome threshold               │
│  • Age and die if energy depleted (natural selection)               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ all agents live in
┌──────────────────────────▼──────────────────────────────────────────┐
│  LAYER 0: MOUSEION SUBSTRATE + ENVIRONMENT                          │
│  • Resource pools (energy, compute, data, attention, knowledge, trust)│
│  • Niche registry ("job board" of open functional roles)            │
│  • Knowledge store (durable records with provenance)                │
│  • Event bus (pub/sub for cross-system signals)                     │
│  • Spatial grid + proximity calculation                             │
│  • Resource regeneration + selection pressure (tick-driven)         │
└─────────────────────────────────────────────────────────────────────┘
```

## The MoltBook Shell/Flesh Pattern

Following BraPil/Agentic-AI-Architect's MoltBook pattern:

**Shell (stable, rarely changes):**
- `organic_agentic_autodev/mouseion/contracts.py` — Pydantic schemas, enums, typed event contracts
- `organic_agentic_autodev/core/genome.py` — Genome data class (behavioral tendencies)
- `organic_agentic_autodev/slime_mold/signal.py` — Signal data class (chemical-analog messages)
- All `__init__.py` public APIs

**Flesh (replaceable, technology-specific):**
- `organic_agentic_autodev/mouseion/substrate.py` — In-memory implementation (swap → SQLite → PostgreSQL)
- `organic_agentic_autodev/slime_mold/pathfinder.py` — NetworkX implementation (swap → custom graph)
- LLM integration (future) — swap OpenAI → Anthropic → local OSS
- Vector store (future) — swap in-memory → FAISS → Qdrant

## Data Flow

```
External stimulus / tick
    ↓
Environment.tick()
    ├── ResourcePool.deposit() × all pools (regeneration)
    ├── Niche.tick() × all niches (urgency aging)
    ├── Environment._rebuild_proximity_cache() (spatial proximity)
    └── StemCell.step() × all agents
            ├── _seek_resources() → ResourcePool.draw()
            ├── _scan_proximity() → ProximitySignal list
            ├── _evaluate_opportunities() → Niche.genome_affinity()
            ├── _attempt_differentiation() → Environment.fill_niche()
            │       └── Mouseion.emit(DIFFERENTIATION_COMPLETED)
            └── _age() → energy decay

SlimeMoldNetwork.tick()
    ├── Pathfinder.tick() → edge decay + exploration
    └── _node_accumulator decay

Body.step()
    ├── Organ.step() × all organs
    │       ├── energy redistribution
    │       ├── dead cell removal
    │       └── Organ._produce_synthesis() → Mouseion.store_knowledge()
    ├── Body._synthesise_vision() → Mouseion.store_knowledge()
    ├── Body._broadcast_vision() → SlimeMoldNetwork.broadcast()
    └── Body._self_improvement_cycle() → fitness scoring
```

## Agent Lifecycle State Machine

```
    CREATE
      │
      ▼
  [STEM_CELL] ←─── no signal / signal decay
      │
      │ signal accumulates above threshold
      │ + enough energy
      │ + matching open niche
      ▼
  [DIFFERENTIATING]
      │
      │ niche filled → reward granted
      ▼
  [DIFFERENTIATED CELL]
      │
      │ compatible cells cluster in proximity
      │ slime mold paths reinforce
      ▼
  [ORGAN MEMBER]
      │
      │ organ reports to Body
      ▼
  [BODY CONTRIBUTOR]
      │
      │ energy → 0
      ▼
    [DEAD]
```

## Key Design Decisions

### 1. Consequence-Driven Behaviour
There is no reward shaping from outside. Agents gain energy by filling niches
and lose it by aging. The fitness landscape is the consequence system.

### 2. Local Information Only
No agent has global visibility. Each agent only knows:
- Its own genome and energy
- What's in its proximity radius
- What's in the Mouseion (shared, but query-based)

Emergent complexity arises from these local interactions.

### 3. Genome as Probability Distribution
The genome doesn't dictate actions — it biases probabilities:
- `curiosity=0.9` → agent *tends* to seek knowledge
- `cooperation=0.8` → agent *tends* to offer resources
- `risk_tolerance=0.3` → agent *tends* toward safe, conservative choices

This produces diversity within the same architecture.

### 4. Compassion as First-Class Value
`compassion` is one of the 8 genome traits, biased slightly above 0.5 even
in random genomes. The Guardian role specifically monitors for struggling
agents and emits DANGER signals. The Body's fitness function weights
compassion impact.

This is deliberate: we want a system that cares about the wellbeing of its
own members and, by extension, the humans and AI it serves.

## Extended Architecture (Built as Flesh)

The following components extend the core architecture **without altering its
shell contracts** — each maps onto an existing layer as *flesh* per the MoltBook
pattern. All of these are now **implemented** (Phase 0 features + the Phase 1–3
knowledge/cognition work); this section documents how they attach. See
`CLAUDE.md` §8 for live phase status and `docs/roadmap.md` for design detail.

```
┌─────────────────────────────────────────────────────────────────────┐
│  COGNITION (flesh on Layer 2: Cells)                                │
│  • CognitiveCell wraps Cell with an LLM decision step               │
│  • Genome traits → system-prompt bias (qualitative instructions)    │
│  • Structured output via tool use → validated knowledge records     │
│  • Providers: Anthropic (default) / OpenAI — hot-swappable          │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE (flesh on Layer 0: Mouseion)                           │
│  • AbstractMouseionBackend protocol; MemoryBackend stays default    │
│  • SQLiteBackend (WAL + FTS5) for durable storage                   │
│  • FAISS vector store → semantic_query() additive API               │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  AUTORESEARCH (flesh on Layer 4: Body self-improvement)             │
│  • Proposer → Runner → Evaluator → commit/rollback                  │
│  • Fixed-budget experiments on system parameters                    │
│  • Compassion guard rejects harmful proposals (stays in code)       │
│  • ProposalCognition seam (Phase 3): LLM picks order + direction +  │
│    rationale; bounds/guard never leave the Proposer                 │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE WIKI (flesh on Layer 0: Mouseion) — Phase 1–2            │
│  • Karpathy ingest / query / lint over KnowledgeRecordV0 (tagged)   │
│  • WikiCognition seam (deterministic default / LLM) for synthesis   │
│  • Pluggable Retriever (lexical default / vector); answer-reuse     │
│  • WikiHealthMonitor → lint/query health as observability SLIs      │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  DASHBOARD (observer; reads all layers)                             │
│  • FastAPI + WebSocket live tick broadcasting                       │
│  • Vanilla JS + Chart.js, no build step                             │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  DISTRIBUTED (orchestration around Layer 0)                         │
│  • Async environments sharing one persistent Mouseion               │
│  • Inter-Body SYNC signal bridge (optional Redis Pub/Sub flesh)     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why these are flesh, not shell

None of these components required a change to `mouseion/contracts.py`,
`genome.py`, or `signal.py` (the shell). They attach to existing extension
points:

- **Cognition** subclasses `Cell` and uses the existing `store_knowledge()` API
- **Persistence** swaps the storage internals behind the unchanged `Mouseion` API
- **Autoresearch** fills in the existing `Body._self_improvement_cycle()` stub
- **Dashboard** is a read-only observer using existing `snapshot()` methods
- **Distributed** orchestrates existing `Environment.tick()` loops
- **Knowledge wiki** rides on the stable `KnowledgeRecordV0` contract via tags
  (`wiki:source`/`wiki:page`/`wiki:answer`) — no new `EventKind`, no shell edits
- **Observability SLIs** for wiki health reuse the existing `SLIMeasurementV0` /
  `SLODefinitionV0` contracts (only *additive* `SLIKind` enum members)

This is the MoltBook promise validated: the architecture was designed so that
the most significant new capabilities are additive flesh.
