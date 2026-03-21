"""
src/evolution/mutator.py

Genome mutation and drift across generations.

When a StemCell divides (spawns a child), the child inherits a mutated
copy of the parent's Genome.  This is the primary driver of evolutionary
adaptation over generations.

Mutation types:
  - Point mutation: small Gaussian perturbation to a single trait
  - Drift: random walk over all traits simultaneously
  - Crossover: blend two parent genomes (when two agents collaborate deeply)
  - Inversion: a trait value flips toward its complement (rare)

The mutation rate and sigma are themselves subject to meta-mutation,
allowing the system to find the right exploration/exploitation balance.
"""

from __future__ import annotations

import random

from src.core.genome import Genome
from src.utils.helpers import clamp, get_logger

logger = get_logger("evolution.mutator")


class Mutator:
    """
    Controls genome mutation across agent generations.

    Parameters
    ----------
    base_rate:
        Probability that any single trait mutates during reproduction.
    base_sigma:
        Standard deviation of Gaussian perturbation when mutation occurs.
    inversion_prob:
        Probability of a full trait inversion (value → 1 - value).
    meta_mutate:
        If True, mutation parameters themselves drift slightly each generation.
    """

    def __init__(
        self,
        base_rate: float = 0.05,
        base_sigma: float = 0.08,
        inversion_prob: float = 0.01,
        meta_mutate: bool = True,
        rng: random.Random | None = None,
    ) -> None:
        self.base_rate = base_rate
        self.base_sigma = base_sigma
        self.inversion_prob = inversion_prob
        self.meta_mutate = meta_mutate
        self.rng = rng or random.Random()
        self._generation = 0

    def reproduce(self, parent: Genome) -> Genome:
        """
        Create a child genome from a single parent.
        Models asexual reproduction / budding.
        """
        self._generation += 1
        rate = self.base_rate
        sigma = self.base_sigma

        # Meta-mutation: rate and sigma drift slightly
        if self.meta_mutate:
            rate = clamp(rate + self.rng.gauss(0, 0.005), 0.001, 0.3)
            sigma = clamp(sigma + self.rng.gauss(0, 0.005), 0.005, 0.3)

        kwargs: dict[str, float] = {}
        for trait in Genome._trait_names():
            value = getattr(parent, trait)
            if self.rng.random() < rate:
                if self.rng.random() < self.inversion_prob:
                    value = 1.0 - value          # inversion
                else:
                    value = clamp(value + self.rng.gauss(0, sigma))  # point mutation
            kwargs[trait] = value

        kwargs["differentiation_threshold"] = clamp(
            parent.differentiation_threshold + self.rng.gauss(0, 0.02)
        )
        kwargs["differentiation_min_energy"] = clamp(
            parent.differentiation_min_energy + self.rng.gauss(0, 0.02)
        )
        child = Genome(**kwargs)
        logger.debug("Generation %d: mutated genome — dominant=%s",
                     self._generation, child.dominant_trait())
        return child

    def sexual_reproduce(self, parent_a: Genome, parent_b: Genome) -> Genome:
        """
        Create a child genome from two parents via crossover + mutation.
        Models deep collaboration between two agents.
        """
        # First crossover
        crossed = parent_a.crossover(parent_b, rng=self.rng)
        # Then mutate the crossed child
        return self.reproduce(crossed)

    @property
    def generation(self) -> int:
        return self._generation
