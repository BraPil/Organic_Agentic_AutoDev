"""
src/evolution/selector.py

Environmental selection pressure.

The Selector applies Darwinian pressure to the agent population:
  - Low-fitness agents lose energy faster (negative selection)
  - High-fitness agents are given opportunities to reproduce (positive selection)
  - Neutral fitness agents survive but do not proliferate

The Selector operates at the Environment level, not on individual agents.
It observes the population each tick and adjusts the selective pressure based
on overall ecosystem health — like a dynamic carrying capacity.

Key properties:
  - Soft selection: agents are weakened, not killed outright
  - Tournament selection: potential parents are chosen by fitness tournament
  - Carrying capacity: the environment limits population growth
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from organic_agentic_autodev.evolution.fitness import FitnessEvaluator, FitnessVector
from organic_agentic_autodev.utils.helpers import get_logger

if TYPE_CHECKING:
    from organic_agentic_autodev.core.stem_cell import StemCell
    from organic_agentic_autodev.core.environment import Environment

logger = get_logger("evolution.selector")


class Selector:
    """
    Applies selective pressure to the agent population each epoch.

    Parameters
    ----------
    carrying_capacity:
        Maximum sustainable population.  Above this, pressure increases.
    selection_strength:
        How aggressively low-fitness agents are penalised (0 = neutral, 1 = harsh).
    reproduction_threshold:
        Minimum fitness.overall required to be eligible to reproduce.
    """

    def __init__(
        self,
        carrying_capacity: int = 50,
        selection_strength: float = 0.3,
        reproduction_threshold: float = 0.4,
        rng: random.Random | None = None,
    ) -> None:
        self.carrying_capacity = carrying_capacity
        self.selection_strength = selection_strength
        self.reproduction_threshold = reproduction_threshold
        self.rng = rng or random.Random()
        self._evaluator = FitnessEvaluator()
        self._epoch = 0

    def apply(self, env: "Environment") -> dict:
        """
        Apply one round of selection pressure to the population.
        Returns a summary of selection events.
        """
        self._epoch += 1
        agents = env.all_agents()
        if not agents:
            return {"epoch": self._epoch, "penalised": 0, "eligible_parents": 0}

        # Rank agents by fitness
        ranked = self._evaluator.rank_agents(agents)

        # Apply negative selection to bottom fraction
        n = len(ranked)
        bottom_cutoff = max(1, int(n * 0.2))
        penalised = 0
        for agent, fv in ranked[-bottom_cutoff:]:
            penalty = self.selection_strength * (1.0 - fv.overall) * 2.0
            agent.energy = max(0.0, agent.energy - penalty)
            penalised += 1

        # Reward top performers (resource bonus)
        top_cutoff = max(1, int(n * 0.1))
        for agent, fv in ranked[:top_cutoff]:
            bonus = self.selection_strength * fv.overall * 1.5
            agent.energy = agent.energy + bonus

        # Identify eligible parents
        eligible = [
            (agent, fv) for agent, fv in ranked
            if fv.overall >= self.reproduction_threshold
        ]

        # If below carrying capacity, eligible agents can spawn
        new_agents = []
        if n < self.carrying_capacity and eligible:
            parent_agent, parent_fv = self.rng.choice(eligible)
            new_agent = self._spawn(parent_agent, env)
            if new_agent:
                new_agents.append(new_agent)

        return {
            "epoch": self._epoch,
            "population": n,
            "penalised": penalised,
            "eligible_parents": len(eligible),
            "spawned": len(new_agents),
        }

    def _spawn(self, parent: "StemCell", env: "Environment") -> "StemCell | None":
        """Create a child StemCell from a parent via reproduction."""
        from organic_agentic_autodev.core.stem_cell import StemCell
        from organic_agentic_autodev.evolution.mutator import Mutator

        if parent.energy < 8.0:
            return None  # not enough energy to reproduce

        mutator = Mutator(rng=self.rng)
        child_genome = mutator.reproduce(parent.genome)
        child = StemCell(
            genome=child_genome,
            initial_energy=parent.energy * 0.3,
            parent_id=parent.agent_id,
            rng=random.Random(self.rng.randint(0, 2**31)),
        )
        child.generation = parent.generation + 1
        parent.energy *= 0.7  # reproduction costs the parent energy

        env.register(child)
        logger.info("Agent %s spawned child %s (gen=%d)", parent.agent_id, child.agent_id, child.generation)
        return child

    def tournament_select(
        self, agents: list["StemCell"], k: int = 3
    ) -> "StemCell | None":
        """Select one agent via tournament selection."""
        if not agents:
            return None
        candidates = self.rng.sample(agents, min(k, len(agents)))
        ranked = self._evaluator.rank_agents(candidates)
        return ranked[0][0] if ranked else None
