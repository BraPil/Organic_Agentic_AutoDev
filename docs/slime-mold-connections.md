# Slime Mold Connections

## Biological Grounding

*Physarum polycephalum* is a slime mold famous for its ability to solve the
Travelling Salesman problem and recreate the Tokyo rail network without any
central planning. It does this through a simple local rule:

> **Tubes that carry more material grow thicker; tubes that carry less material
> grow thinner and eventually disappear.**

This positive feedback loop produces globally optimal (near-shortest) paths
through purely local, decentralized computation.

## Our Implementation

We model this with three components:

### 1. `Pathfinder` (conductance graph)

The Pathfinder maintains a NetworkX directed graph where:
- **Nodes** = agent IDs
- **Edge weight** = conductance (0.01 → 1.0)

Conductance rules:
- `reinforce(u, v)`: +0.1 per successful signal delivery (tube thickens)
- `tick()`: -0.02 per tick per edge (passive decay — tube thins)
- `weaken(u, v)`: -0.1 for failed routing
- Edges below `MIN_CONDUCTANCE * 1.1` with zero flux are pruned

### 2. `Signal` (chemical message)

A Signal carries:
- `signal_type`: FOOD / DANGER / OPPORTUNITY / KNOWLEDGE / SYNC
- `strength`: attenuates 30% per hop
- `max_hops`: prevents infinite propagation

Analogy: chemical gradients in the slime mold's cytoplasm.

### 3. `SlimeMoldNetwork` (integrated layer)

Combines Pathfinder + Signal routing:
- `broadcast(signal, origin)`: sends to all direct neighbours
- `send_signal(signal, src, dst)`: routes along highest-conductance path
- Path success → `reinforce()` each hop
- Path failure → `weaken()` the attempted edge

## Exploratory Tendrils

Each tick, with probability `EXPLORE_PROB = 0.05`, the Pathfinder randomly
connects two agents. This models the slime mold's pseudopod exploration:

```
if rng.random() < EXPLORE_PROB:
    src, dst = rng.sample(agent_ids, 2)
    self.ensure_edge(src, dst)  # initial conductance = 0.05
```

New connections start weak. They only persist if agents actually use them.

## Cluster Detection → Organ Formation

The most powerful emergent behavior: when strongly connected subgraphs are
detected, they become candidate Organs.

```python
def detect_clusters(self, min_conductance=0.3):
    strong = nx.DiGraph()
    for u, v, d in self._graph.edges(data=True):
        if d["conductance"] >= min_conductance:
            strong.add_edge(u, v)
    return list(nx.weakly_connected_components(strong))
```

Cells that exchange many signals (because their roles are compatible) will
reinforce paths between them. Their cluster will eventually exceed the
`min_conductance` threshold and be detected as an Organ candidate.

This is the bridge between the slime mold layer and the Organ layer —
**Organ formation is a function of communication density, not central design.**

## Signal Types and Behaviors

| Signal | Source | Effect |
|--------|--------|--------|
| FOOD | Environment / high-energy agents | Recipients move toward source |
| DANGER | Guardian cells | Recipients reduce risk-taking |
| OPPORTUNITY | Connector cells | Recipients scan new niches |
| KNOWLEDGE | Researcher cells | Recipients draw from Mouseion |
| SYNC | Body / Organs | Coordination pulse |

## Network Health Metrics

The `SlimeMoldNetwork.summary()` returns:
- `nodes`: number of agents connected
- `edges`: number of active connections
- `avg_conductance`: mean edge strength (proxy for network health)
- `signals_delivered`: total message deliveries

A healthy network has high avg_conductance on edges between compatible roles
and low avg_conductance (or no edges) between incompatible ones.
This is the network expressing the ecosystem's actual workflow.

## Comparison to Fixed Topologies

| Aspect | Fixed (hub-and-spoke) | Slime Mold (ours) |
|--------|----------------------|-------------------|
| Design | Explicit by architect | Emerges from usage |
| Resilience | Single point of failure | Self-healing |
| Efficiency | Optimal for known workload | Adapts to actual workload |
| New agents | Must be wired in | Self-register and connect |
| Bottlenecks | Hidden until overload | Visible as low conductance |
