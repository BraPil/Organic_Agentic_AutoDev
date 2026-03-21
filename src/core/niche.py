"""
src/core/niche.py

Niche — an open functional role the ecosystem needs filled.

Niches are the ecosystem's "job board."  When a niche goes unfilled, urgency
grows.  When filled, the filling agent receives a resource reward.  Niches
can expire if urgency falls too low (the ecosystem evolved past the need).

Niche types map to AgentRole specialisations, providing the selection
pressure that drives StemCell differentiation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.mouseion.contracts import AgentRole, ResourceKind


# Trait weights that describe how well a Genome fits each role
ROLE_GENOME_WEIGHTS: dict[AgentRole, dict[str, float]] = {
    AgentRole.RESEARCHER: {
        "curiosity": 1.0,
        "creativity": 0.7,
        "persistence": 0.5,
        "risk_tolerance": 0.3,
    },
    AgentRole.CODER: {
        "persistence": 1.0,
        "specialisation": 0.8,
        "creativity": 0.5,
        "risk_tolerance": 0.4,
    },
    AgentRole.CRITIC: {
        "persistence": 0.8,
        "resilience": 0.6,
        "risk_tolerance": 0.3,
        "cooperation": 0.4,
    },
    AgentRole.SYNTHESIZER: {
        "creativity": 1.0,
        "cooperation": 0.8,
        "curiosity": 0.6,
        "compassion": 0.5,
    },
    AgentRole.CURATOR: {
        "persistence": 0.9,
        "cooperation": 0.7,
        "compassion": 0.6,
        "specialisation": 0.5,
    },
    AgentRole.CONNECTOR: {
        "cooperation": 1.0,
        "compassion": 0.8,
        "curiosity": 0.6,
        "risk_tolerance": 0.5,
    },
    AgentRole.INNOVATOR: {
        "creativity": 1.0,
        "risk_tolerance": 0.9,
        "curiosity": 0.8,
        "specialisation": 0.3,
    },
    AgentRole.GUARDIAN: {
        "resilience": 1.0,
        "compassion": 0.9,
        "persistence": 0.7,
        "cooperation": 0.6,
    },
}


@dataclass
class Niche:
    """
    A concrete niche in the ecosystem.

    Niches are not static job descriptions — they evolve.  Urgency increases
    each tick the niche is unfilled.  Once filled, the reward is paid out to
    the filling agent and the niche is marked as occupied.
    """

    niche_id: str
    role: AgentRole
    description: str
    urgency: float = 0.5               # [0, 1] — higher = more pressing
    base_reward: dict[ResourceKind, float] = field(default_factory=dict)
    filled_by: str | None = None
    age_ticks: int = 0
    urgency_growth_rate: float = 0.02  # urgency increase per unfilled tick
    urgency_decay_rate: float = 0.01   # urgency decrease per tick when filled

    def tick(self) -> None:
        """Advance the niche by one simulation tick."""
        self.age_ticks += 1
        if self.filled_by is None:
            self.urgency = min(1.0, self.urgency + self.urgency_growth_rate)
        else:
            self.urgency = max(0.0, self.urgency - self.urgency_decay_rate)

    @property
    def is_open(self) -> bool:
        return self.filled_by is None

    def effective_reward(self) -> dict[ResourceKind, float]:
        """Reward scales with urgency — the more needed, the better the payoff."""
        return {k: v * (1.0 + self.urgency) for k, v in self.base_reward.items()}

    def genome_affinity(self, genome: "Genome") -> float:  # type: ignore[name-defined]
        """How well does this genome fit this niche?"""
        weights = ROLE_GENOME_WEIGHTS.get(self.role, {})
        return genome.affinity_score(weights)

    def __repr__(self) -> str:
        status = "open" if self.is_open else f"filled by {self.filled_by}"
        return f"Niche({self.role.value}, urgency={self.urgency:.2f}, {status})"
