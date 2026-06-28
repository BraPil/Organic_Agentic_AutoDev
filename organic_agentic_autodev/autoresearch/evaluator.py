"""
src/autoresearch/evaluator.py

EcosystemEvaluator — a single scalar fitness for the whole ecosystem.

The autoresearch loop needs a before/after metric to decide whether an
experiment helped. This evaluator condenses ecosystem health into one score in
[0, 1], combining:

  - mean agent fitness        (are individual agents thriving?)
  - knowledge growth          (is the corpus enriching?)
  - energy headroom           (is the system solvent, not starving?)
  - niche fill rate           (are the ecosystem's needs being met?)

It deliberately reuses the existing FitnessEvaluator for the agent term so the
ecosystem's value system stays consistent across modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from organic_agentic_autodev.evolution.fitness import FitnessEvaluator
from organic_agentic_autodev.mouseion.contracts import ResourceKind
from organic_agentic_autodev.utils.helpers import clamp

if TYPE_CHECKING:
    from organic_agentic_autodev.core.environment import Environment


class EcosystemEvaluator:
    """Computes a single ecosystem-fitness scalar for autoresearch."""

    def __init__(self, initial_energy: float = 1000.0) -> None:
        self._agent_eval = FitnessEvaluator()
        self._initial_energy = initial_energy
        self._last_knowledge_count = 0

    def score(self, env: "Environment") -> float:
        """Return ecosystem fitness in [0, 1] (higher is better)."""
        agents = env.all_agents()

        # 1. Mean agent fitness
        if agents:
            ranked = self._agent_eval.rank_agents(agents)
            mean_agent = sum(fv.overall for _, fv in ranked) / len(ranked)
        else:
            mean_agent = 0.0

        # 2. Knowledge growth since last evaluation (normalised)
        kc = env.mouseion.knowledge_count()
        growth = max(0, kc - self._last_knowledge_count)
        self._last_knowledge_count = kc
        knowledge_term = clamp(growth / 10.0)

        # 3. Energy headroom
        energy = env.mouseion.resource_level(ResourceKind.ENERGY)
        energy_term = clamp(energy / self._initial_energy)

        # 4. Niche fill rate
        with env._niche_lock:
            total = len(env._niches)
            filled = sum(1 for n in env._niches.values() if not n.is_open)
        niche_term = (filled / total) if total else 1.0

        return clamp(
            0.40 * mean_agent
            + 0.25 * knowledge_term
            + 0.20 * energy_term
            + 0.15 * niche_term
        )

    def reset_baseline(self, env: "Environment") -> None:
        """Sync the knowledge-growth baseline (call before a fresh measurement run)."""
        self._last_knowledge_count = env.mouseion.knowledge_count()
