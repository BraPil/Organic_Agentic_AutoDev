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
- `src/mouseion/contracts.py` — Pydantic schemas, enums, typed event contracts
- `src/core/genome.py` — Genome data class (behavioral tendencies)
- `src/slime_mold/signal.py` — Signal data class (chemical-analog messages)
- All `__init__.py` public APIs

**Flesh (replaceable, technology-specific):**
- `src/mouseion/substrate.py` — In-memory implementation (swap → SQLite → PostgreSQL)
- `src/slime_mold/pathfinder.py` — NetworkX implementation (swap → custom graph)
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
