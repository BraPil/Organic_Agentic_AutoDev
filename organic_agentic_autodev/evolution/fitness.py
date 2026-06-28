"""
src/evolution/fitness.py

Multi-dimensional fitness evaluation for agents and organs.

Fitness in this system is NOT a single number — it is a vector of scores
across dimensions that reflect the ecosystem's values:
  - Resource efficiency  (how well the agent converts resources into output)
  - Knowledge contribution (how much the agent enriches the Mouseion)
  - Cooperation index    (how much the agent enables others)
  - Resilience           (how well the agent survives adversity)
  - Compassion impact    (how much the agent reduces harm to others)
  - Specialisation depth (how deeply the agent has developed its niche)

Overall fitness is a weighted sum of these dimensions.  The weights
themselves can evolve — the ecosystem can develop its own value system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from organic_agentic_autodev.utils.helpers import clamp

if TYPE_CHECKING:
    from organic_agentic_autodev.core.stem_cell import StemCell
    from organic_agentic_autodev.organisms.organ import Organ


@dataclass
class FitnessVector:
    """A multi-dimensional fitness evaluation for one agent or organ."""
    resource_efficiency: float = 0.0
    knowledge_contribution: float = 0.0
    cooperation_index: float = 0.0
    resilience: float = 0.0
    compassion_impact: float = 0.0
    specialisation_depth: float = 0.0

    # Weights — can be evolved by the ecosystem
    weights: dict[str, float] = field(default_factory=lambda: {
        "resource_efficiency": 0.2,
        "knowledge_contribution": 0.25,
        "cooperation_index": 0.2,
        "resilience": 0.1,
        "compassion_impact": 0.15,
        "specialisation_depth": 0.1,
    })

    @property
    def overall(self) -> float:
        dimensions = {
            "resource_efficiency": self.resource_efficiency,
            "knowledge_contribution": self.knowledge_contribution,
            "cooperation_index": self.cooperation_index,
            "resilience": self.resilience,
            "compassion_impact": self.compassion_impact,
            "specialisation_depth": self.specialisation_depth,
        }
        total = sum(
            dimensions[k] * self.weights.get(k, 0.0)
            for k in dimensions
        )
        return clamp(total)

    def to_dict(self) -> dict[str, float]:
        return {
            "resource_efficiency": self.resource_efficiency,
            "knowledge_contribution": self.knowledge_contribution,
            "cooperation_index": self.cooperation_index,
            "resilience": self.resilience,
            "compassion_impact": self.compassion_impact,
            "specialisation_depth": self.specialisation_depth,
            "overall": self.overall,
        }

    def __repr__(self) -> str:
        return f"FitnessVector(overall={self.overall:.3f}, {self.to_dict()})"


class FitnessEvaluator:
    """
    Evaluates fitness of agents and organs against ecosystem criteria.
    """

    def evaluate_agent(self, agent: "StemCell", knowledge_contributed: int = 0) -> FitnessVector:
        """Evaluate a single agent's fitness."""
        genome = agent.genome
        energy_ratio = clamp(agent.energy / 20.0)  # normalised against target

        return FitnessVector(
            resource_efficiency=energy_ratio,
            knowledge_contribution=clamp(knowledge_contributed / 10.0),
            cooperation_index=genome.cooperation,
            resilience=genome.resilience,
            compassion_impact=genome.compassion,
            specialisation_depth=(
                getattr(agent, "specialisation_score", 0.0)
                if agent.is_differentiated else 0.0
            ),
        )

    def evaluate_organ(self, organ: "Organ") -> FitnessVector:
        """Evaluate an organ's collective fitness."""
        snap = organ.snapshot()
        return FitnessVector(
            resource_efficiency=clamp(snap["mean_energy"] / 15.0),
            knowledge_contribution=clamp(snap["knowledge_records_produced"] / 20.0),
            cooperation_index=clamp(snap["size"] / 6.0),
            resilience=clamp(snap["age_ticks"] / 50.0),
            compassion_impact=snap["mean_specialisation"],
            specialisation_depth=snap["mean_specialisation"],
        )

    def rank_agents(self, agents: list["StemCell"],
                    knowledge_map: dict[str, int] | None = None) -> list[tuple["StemCell", FitnessVector]]:
        """Rank agents by overall fitness (descending)."""
        km = knowledge_map or {}
        scored = [
            (agent, self.evaluate_agent(agent, km.get(agent.agent_id, 0)))
            for agent in agents
        ]
        scored.sort(key=lambda x: x[1].overall, reverse=True)
        return scored
