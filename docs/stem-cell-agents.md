# Stem Cell Agents

## Biological Grounding

Real stem cells are defined by two properties:
1. **Self-renewal** — they can divide to produce more stem cells
2. **Potency** — they can differentiate into specialized cell types

Our StemCell agents mirror both:
- `Selector._spawn()` models self-renewal (asexual reproduction via Genome mutation)
- `StemCell._attempt_differentiation()` models potency (commitment to a role)

## The Four Drives

A StemCell's step loop is organized around four biological drives:

### 1. Seek Resources (Energy)
```python
def _seek_resources(self, env):
    drawn = env.mouseion.draw_resource(ResourceKind.ENERGY, ...)
    self.energy += drawn
```
Without energy, the agent dies. High-curiosity agents also seek DATA.
This is the most primal drive — resource acquisition for survival.

### 2. Scan Proximity
```python
def _scan_proximity(self, env):
    signals = env.proximity_signals(self.agent_id)
    # What roles are my neighbours filling?
    # What do they need? What can I offer?
```
The agent observes its neighbourhood (spatial radius). Dense occupancy of a
role signals competition; absence of a role signals opportunity.

### 3. Evaluate Opportunities (Niches)
```python
def _evaluate_opportunities(self, env):
    best = env.best_niche_for(self)
    affinity = best.genome_affinity(self.genome)
    signal_strength = affinity * best.urgency * 0.15
    self._accumulate_diff_signal(best.role, signal_strength)
```
The agent queries the Mouseion's niche registry for open roles.
Niches score each role by `urgency × genome_affinity`.
The signal accumulates in the `_diff_signals` dict.

### 4. Seek What Is in Proximity
Proximity signals also include what neighbours are *seeking* and *offering*.
An agent with low energy that sees a high-energy neighbour offering energy
can move toward it. This is the ecosystem's social layer.

## Differentiation

Differentiation triggers when three conditions are met:
1. `signal.strength >= genome.differentiation_threshold`
2. `energy >= genome.differentiation_min_energy * 20`
3. An open niche of the target role exists

Once these conditions are met:
- The niche is claimed (no other agent can fill it)
- The resource reward is paid out
- `role` is set to the target AgentRole
- `_differentiated = True` (irreversible)
- `DIFFERENTIATION_COMPLETED` event is emitted to the Mouseion

## Genome Impact on Differentiation

| Trait | Effect on Differentiation |
|-------|--------------------------|
| `curiosity` | Increases energy drawn (more signal exposure) |
| `risk_tolerance` | Scans more niches simultaneously |
| `persistence` | Prevents signal decay (holds commitment longer) |
| `specialisation` | Lowers the effective niche affinity threshold |
| `differentiation_threshold` | Genome-encoded minimum signal to commit |

## Death

Agents die when `energy <= 0`. The Environment removes them:
```python
if agent.energy <= 0:
    dead_agents.append(agent.agent_id)
# ...
for agent_id in dead_agents:
    self.deregister(agent_id)
```

Death is permanent. This creates selection pressure — agents that fail to
acquire resources or fill niches don't persist to reproduce.

## Reproduction (via Selector)

The `Selector` class manages population dynamics:
- Every N ticks, it ranks agents by fitness
- Bottom performers lose energy (negative selection)
- Top performers are given reproduction opportunities
- If population < carrying_capacity, a new StemCell is spawned with a
  mutated copy of the parent's Genome

```python
child_genome = mutator.reproduce(parent.genome)
child = StemCell(genome=child_genome, initial_energy=parent.energy * 0.3)
child.generation = parent.generation + 1
```

Over generations, genomes evolve toward better fitness in the current ecosystem.
