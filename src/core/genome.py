"""
src/core/genome.py

The Genome — an agent's "DNA."

Encodes behavioral tendencies that shape how the agent perceives and
responds to its environment.  The Genome is NOT a fixed instruction set —
it is a probabilistic disposition system that can mutate across generations.

Traits are floats in [0, 1]:
  curiosity          — drive to explore unknown niches and opportunities
  risk_tolerance     — willingness to attempt high-variance actions
  cooperation        — preference for sharing resources vs. competing
  specialisation     — pull toward deepening one skill vs. staying broad
  compassion         — weight given to the wellbeing of other agents
  resilience         — recovery rate after energy loss or failure
  creativity         — tendency to generate novel approaches
  persistence        — resistance to abandoning a chosen path
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import ClassVar

from src.utils.helpers import clamp


@dataclass
class Genome:
    """Immutable-ish behavioral blueprint for a StemCell or differentiated Cell."""

    # Core traits — all in [0, 1]
    curiosity: float = 0.5
    risk_tolerance: float = 0.5
    cooperation: float = 0.5
    specialisation: float = 0.5
    compassion: float = 0.6          # Default slightly elevated — compassion is first-class
    resilience: float = 0.5
    creativity: float = 0.5
    persistence: float = 0.5

    # Differentiation thresholds — how much signal is needed to commit to a niche
    differentiation_threshold: float = 0.7
    # Minimum energy fraction required to attempt differentiation
    differentiation_min_energy: float = 0.4

    # Mutation parameters
    MUTATION_RATE: ClassVar[float] = 0.05
    MUTATION_SIGMA: ClassVar[float] = 0.08

    def __post_init__(self) -> None:
        self._clamp_traits()

    def _clamp_traits(self) -> None:
        for attr in self._trait_names():
            setattr(self, attr, clamp(getattr(self, attr)))

    @staticmethod
    def _trait_names() -> list[str]:
        return [
            "curiosity", "risk_tolerance", "cooperation",
            "specialisation", "compassion", "resilience",
            "creativity", "persistence",
        ]

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def random(cls, rng: random.Random | None = None) -> "Genome":
        """Fully random genome — used for first-generation StemCells."""
        r = rng or random
        return cls(
            curiosity=r.random(),
            risk_tolerance=r.random(),
            cooperation=r.random(),
            specialisation=r.random(),
            compassion=clamp(r.gauss(0.6, 0.15)),  # slightly biased toward compassion
            resilience=r.random(),
            creativity=r.random(),
            persistence=r.random(),
        )

    @classmethod
    def blank_slate(cls) -> "Genome":
        """Totipotent baseline — neutral on all axes."""
        return cls(
            curiosity=0.5, risk_tolerance=0.5, cooperation=0.5,
            specialisation=0.1,  # start undifferentiated
            compassion=0.6, resilience=0.5, creativity=0.5, persistence=0.5,
        )

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def mutate(self, rng: random.Random | None = None) -> "Genome":
        """
        Return a new Genome with small random perturbations.
        Models genetic drift and mutation across generations.
        """
        r = rng or random
        kwargs: dict[str, float] = {}
        for trait in self._trait_names():
            current = getattr(self, trait)
            if r.random() < self.MUTATION_RATE:
                current = clamp(current + r.gauss(0, self.MUTATION_SIGMA))
            kwargs[trait] = current
        kwargs["differentiation_threshold"] = clamp(
            self.differentiation_threshold + r.gauss(0, 0.02)
        )
        kwargs["differentiation_min_energy"] = clamp(
            self.differentiation_min_energy + r.gauss(0, 0.02)
        )
        return Genome(**kwargs)

    def crossover(self, other: "Genome", rng: random.Random | None = None) -> "Genome":
        """
        Sexual recombination — randomly inherit each trait from either parent.
        Used when two agents 'collaborate' deeply enough to share genetic material.
        """
        r = rng or random
        kwargs: dict[str, float] = {}
        for trait in self._trait_names():
            kwargs[trait] = getattr(self if r.random() < 0.5 else other, trait)
        kwargs["differentiation_threshold"] = (
            self.differentiation_threshold + other.differentiation_threshold
        ) / 2
        kwargs["differentiation_min_energy"] = (
            self.differentiation_min_energy + other.differentiation_min_energy
        ) / 2
        return Genome(**kwargs)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, float]:
        return {t: getattr(self, t) for t in self._trait_names()}

    def dominant_trait(self) -> str:
        traits = self.to_dict()
        return max(traits, key=lambda k: traits[k])

    def affinity_score(self, role_weights: dict[str, float]) -> float:
        """
        Compute how well this Genome matches a role described by trait weights.
        role_weights maps trait names to how important that trait is for the role.
        Returns a score in [0, 1].
        """
        total_weight = sum(abs(w) for w in role_weights.values())
        if total_weight == 0:
            return 0.5
        score = sum(
            getattr(self, trait, 0.5) * weight
            for trait, weight in role_weights.items()
        )
        return clamp(score / total_weight)

    def __repr__(self) -> str:
        traits = ", ".join(f"{k}={v:.2f}" for k, v in self.to_dict().items())
        return f"Genome({traits})"
