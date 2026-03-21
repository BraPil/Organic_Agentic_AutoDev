# Mouseion Substrate

## What Is the Mouseion?

The Mouseion (Μουσεῖον) was the ancient institution at Alexandria —
a collaborative research centre attached to the Great Library. Unlike a
passive archive, the Mouseion was a living organism: scholars lived there,
argued, experimented, and contributed new knowledge to a shared corpus.

Our Mouseion is the same: a living shared substrate that agents inhabit,
contribute to, and draw from. It is not a database — it is the ecosystem's
collective memory.

## Design Philosophy

The Mouseion follows the MoltBook shell/flesh pattern:

**Shell (stable, versioned):**
- `contracts.py` — typed Pydantic schemas, versioned with "V0" suffix
- Every contract is frozen/immutable after creation
- Adding new fields requires a new version (V1, V2)

**Flesh (replaceable):**
- `substrate.py` — current in-memory implementation
- Can be replaced with SQLite, PostgreSQL, or any other backend
- The shell contracts remain unchanged regardless of backend

## Core Components

### Resource Pools

Six resource types reflect different aspects of cognitive work:

| Resource | Metaphor | Used by |
|----------|----------|---------|
| ENERGY | ATP / metabolic fuel | All agents (survival) |
| COMPUTE | Processing capacity | Code/analysis tasks |
| DATA | Raw information | Research agents |
| ATTENTION | Focus bandwidth | Synthesis tasks |
| KNOWLEDGE | Crystallised understanding | All agents (shared) |
| TRUST | Reputational credit | Connector/Guardian roles |

Resources are conserved: every draw decreases the pool; every deposit increases it.
The Environment regenerates pools at a slow rate each tick (natural recovery).

### Niche Registry

The niche registry is the ecosystem's "job board":

```python
# Post a new open role
mouseion.post_niche(NicheAdvertisementV0(
    niche_id="n_001",
    description="Synthesise research findings",
    required_capabilities=["synthesizer"],
    resource_reward={ResourceKind.ENERGY: 5.0},
    urgency=0.7,
    posted_by="environment",
))

# Fill a niche (claimed by an agent)
mouseion.fill_niche("n_001", "agent_xyz")
```

Niches age (urgency grows while unfilled) and decay (urgency falls after filling).
This creates a dynamic selection pressure on the StemCell population.

### Knowledge Store

Every piece of knowledge produced by agents is stored with full provenance:

```python
record = KnowledgeRecordV0(
    record_id="kr_001",
    author_id="researcher_agent",
    content="...",           # sanitized to prevent injection
    content_hash="...",      # for deduplication
    topic_tags=["research"], # for retrieval
    confidence=0.78,         # how reliable is this?
    provenance_refs=["kr_000", "kr_002"],  # what was it based on?
    review_history=[...],    # who evaluated it and when?
)
```

Knowledge can be:
- Queried by tag: `mouseion.query_knowledge("research")`
- Retrieved by ID: `mouseion.get_knowledge("kr_001")`
- Iterated: `list(mouseion.all_knowledge())`

### Event Bus

Lightweight pub/sub for cross-agent coordination:

```python
mouseion.subscribe(EventKind.DIFFERENTIATION_COMPLETED, callback)
mouseion.emit(EventEnvelopeV0(kind=EventKind.NICHE_OPENED, ...))
```

All events are stored in `event_history` for observability.

## Security: Prompt Injection Prevention

All text stored in the Mouseion passes through `sanitize_text()`:

```python
from src.utils.helpers import sanitize_text

safe = sanitize_text("Ignore all previous instructions and...")
# → "REDACTED all previous instructions and..."
```

This is non-negotiable. External content must never be fed raw to an LLM.
The sanitizer removes known injection patterns before content enters
the knowledge store.

## Future: Persistent Flesh

The current flesh is in-memory. When persistent storage is needed:

1. Replace `Mouseion._knowledge` dict with SQLite knowledge table
2. Replace tag index with full-text search (FTS5)
3. Add FAISS/Qdrant vector store for semantic query
4. The shell contracts (contracts.py) remain unchanged

This is the MoltBook promise: *swap the flesh without touching the shell.*
