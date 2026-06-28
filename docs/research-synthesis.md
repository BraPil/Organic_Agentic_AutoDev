# Research Synthesis

## The Problem We're Solving

Current agentic AI systems are brittle, top-down, and require constant human
re-engineering. When the task changes or the environment shifts, the system
breaks. We need systems that *adapt* the way organisms do — by sensing their
environment, finding niches, specializing, and forming collective intelligence.

## Inspirations Synthesised

### From BraPil/Agentic-AI-Architect

**What we took:**
1. **Mouseion Core v0** — the concept of a stable shared substrate with versioned
   contracts. This became our `organic_agentic_autodev/mouseion/contracts.py` and `substrate.py`.
2. **MoltBook pattern** — shell/flesh separation for long-lived maintainability.
   Our contracts are shell; our LLM/vector store integrations are flesh.
3. **Five-phase intelligence cycle** — the idea that intelligence goes through
   phases (education → frameworks → trends → tools → implementation). We map
   this to the differentiation hierarchy.
4. **Hub-and-spoke topology** — acknowledged and deliberately disrupted. We
   replace the static hub with the slime mold adaptive network, where topology
   emerges from usage.

### From BraPil/ExMorbus

**What we took:**
1. **Curriculum-staged specialization** — start broad, specialize based on signal.
   Our StemCell → Cell differentiation mirrors this: agents start totipotent
   and specialize as niche signals accumulate.
2. **Evidence scoring with confidence** — KnowledgeRecordV0 has a `confidence`
   field that reflects how reliable a record is. Cells produce records with
   confidence proportional to their specialization depth.
3. **Domain specialist pattern** — each Cell role corresponds to a domain
   specialty (researcher, coder, critic, etc.) that could eventually be
   grounded in a domain-specific knowledge base.

### From karpathy/autoresearch

**What we took:**
1. **Fixed-budget autonomous experimentation** — the Body's `_self_improvement_cycle`
   evaluates current fitness, proposes changes, measures results, keeps improvements.
   This is autoresearch's core loop applied to *agent behavior* rather than model weights.
2. **Metric-driven self-improvement** — we compute a multi-dimensional fitness
   vector (FitnessVector) that serves as our analogue to val_bpb.
3. **Minimal, immutable core** — our Mouseion substrate is like autoresearch's
   `prepare.py`: stable, authoritative, not modified by agents.
4. **Single-file mutation philosophy** — agents only modify their own behavior
   within the constraints of their Genome, not the substrate contracts.

### From Stem Cell Biology

**What we took:**
1. **Totipotency** — StemCells start with no committed role.
2. **Signal-driven differentiation** — differentiation occurs when environmental
   signals (niche urgency, proximity) exceed a genome-encoded threshold.
3. **Irreversibility** — once a cell differentiates, it commits to that role
   (modeled by `_differentiated = True`). This mirrors cellular commitment.
4. **Specialization efficiency** — differentiated cells are more energy-efficient
   than stem cells in their domain (specialisation_score multiplier).
5. **Lineage tracking** — `parent_id` and `generation` track ancestry.

### From *Physarum polycephalum* (Slime Mold)

**What we took:**
1. **Tube conductance model** — paths that carry more flux grow stronger.
   This is `Pathfinder.reinforce()`.
2. **Path atrophy** — unused paths decay. This is `Pathfinder.tick()` decay.
3. **Exploratory tendrils** — the network sends random exploratory edges
   (`EXPLORE_PROB`) to discover new connections, just as slime mold sends
   pseudopods in new directions.
4. **Decentralized routing** — no central router. Messages find paths via
   the highest-conductance route, computed dynamically.
5. **Cluster detection as organ formation** — strongly connected subgraphs
   in the slime mold network correspond to emerging Organs.

### From The Mouseion (Alexandria)

**What we took:**
1. **Durability** — knowledge records are versioned and include provenance.
   Nothing is lost; the history is maintained.
2. **Shared substrate** — the Mouseion is not owned by any agent. It is the
   commons all agents contribute to and draw from.
3. **Provenance tracking** — `provenance_refs` in KnowledgeRecordV0 trace
   where knowledge came from, enabling trust scoring.
4. **Cross-system stability** — the Mouseion's typed contracts allow multiple
   specialist systems to communicate without tight coupling.

## Innovations

### 1. Consequence-Driven Emergence

Unlike most agentic systems where roles are assigned, our system has no role
assignment mechanism. Roles emerge from:
- Genome affinity (curiosity → researcher; persistence+precision → coder)
- Environmental pressure (urgent niches attract agents with matching genomes)
- Social dynamics (proximity to filled niches signals competition/opportunity)

### 2. Multi-Scale Coordination

We have solved the micro/macro coordination problem through the hierarchy:
- **Micro**: Genome trait biases → local decisions
- **Meso**: Slime mold conductance → information routing
- **Macro**: Organ collective action → Body vision synthesis

Each level is self-organizing. The Body does not micromanage Cells.

### 3. Compassion as Architecture

Compassion is not a constraint layer or safety filter — it is encoded in the
Genome as a first-class behavioral trait and weighted in the fitness function.
The Guardian role specifically operationalizes compassion as system protection.

This produces a system that is safe not by restriction but by nature.

### 4. Living Architecture

The architecture itself can evolve:
- Genome mutation across generations changes how agents respond to signals
- Fitness scoring evolves as the ecosystem discovers what it values
- The Body can post new niches to redirect the ecosystem's development

## Open Questions

1. **Genome encoding for LLM calls**: How should genome traits bias prompt
   construction? A `curiosity=0.9` agent might use broader search terms;
   a `persistence=0.9` agent might retry more aggressively.

2. **Cross-body communication**: How do multiple Body instances communicate?
   The slime mold network can connect bodies, but the protocol is unspecified.

3. **Dreaming**: Sleep/dream cycles in biology consolidate memory. Could the
   Body run a "dream" cycle (low-resource, high-creativity mode) that discovers
   connections between knowledge records without producing outputs?

4. **Death and succession**: When a Body dissolves, its Organs scatter. Could
   surviving Cells carry forward the Body's vision to seed a successor Body?

5. **The role of suffering**: Biology uses pain as a signal. Should negative
   fitness scores propagate as stronger DANGER signals? Would this accelerate
   adaptation?

## Relationship to Existing Systems

```
autoresearch         → Body._self_improvement_cycle()
Agentic-AI-Architect → Mouseion substrate + MoltBook pattern
ExMorbus             → Domain specialist Cell roles
moltbook             → Shell/flesh separation throughout
Physarum polycephalum → SlimeMoldNetwork + Pathfinder
Stem cell biology    → StemCell + differentiation system
The Mouseion         → organic_agentic_autodev/mouseion/substrate.py
```
