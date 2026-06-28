"""
tests/test_genome.py — Unit tests for the Genome class.
"""

import random

import pytest

from organic_agentic_autodev.core.genome import Genome
from organic_agentic_autodev.utils.helpers import clamp


class TestGenomeDefaults:
    def test_blank_slate_has_low_specialisation(self):
        g = Genome.blank_slate()
        assert g.specialisation < 0.2

    def test_all_traits_in_range(self):
        g = Genome.random()
        for trait in Genome._trait_names():
            val = getattr(g, trait)
            assert 0.0 <= val <= 1.0, f"Trait {trait}={val} out of [0,1]"

    def test_compassion_biased_high_in_random(self):
        """Random genomes should have compassion slightly above 0.5 on average."""
        rng = random.Random(0)
        scores = [Genome.random(rng=rng).compassion for _ in range(100)]
        assert sum(scores) / len(scores) > 0.5

    def test_invalid_trait_clamped(self):
        g = Genome(curiosity=2.0, risk_tolerance=-0.5)
        assert g.curiosity == 1.0
        assert g.risk_tolerance == 0.0


class TestGenomeMutation:
    def test_mutate_returns_new_genome(self):
        g = Genome.blank_slate()
        child = g.mutate()
        assert child is not g

    def test_mutate_preserves_trait_range(self):
        rng = random.Random(42)
        g = Genome.random(rng=rng)
        for _ in range(50):
            g = g.mutate(rng=rng)
            for trait in Genome._trait_names():
                val = getattr(g, trait)
                assert 0.0 <= val <= 1.0

    def test_crossover_blends_parents(self):
        rng = random.Random(1)
        parent_a = Genome(curiosity=0.0, creativity=0.0, compassion=0.0,
                          risk_tolerance=0.0, cooperation=0.0, specialisation=0.0,
                          resilience=0.0, persistence=0.0)
        parent_b = Genome(curiosity=1.0, creativity=1.0, compassion=1.0,
                          risk_tolerance=1.0, cooperation=1.0, specialisation=1.0,
                          resilience=1.0, persistence=1.0)
        children = [parent_a.crossover(parent_b, rng=rng) for _ in range(20)]
        # Each trait should come from one of the parents
        for child in children:
            for trait in Genome._trait_names():
                val = getattr(child, trait)
                assert val in (0.0, 1.0), f"Expected 0 or 1 from crossover, got {val}"


class TestGenomeAffinity:
    def test_affinity_score_in_range(self):
        g = Genome.random()
        weights = {"curiosity": 1.0, "creativity": 0.5}
        score = g.affinity_score(weights)
        assert 0.0 <= score <= 1.0

    def test_high_curiosity_genome_prefers_researcher_niche(self):
        from organic_agentic_autodev.core.niche import Niche, ROLE_GENOME_WEIGHTS
        from organic_agentic_autodev.mouseion.contracts import AgentRole, ResourceKind

        g = Genome(curiosity=1.0, creativity=1.0, persistence=0.2,
                   risk_tolerance=0.2, cooperation=0.5, specialisation=0.5,
                   resilience=0.5, compassion=0.6)
        niche = Niche(
            niche_id="test",
            role=AgentRole.RESEARCHER,
            description="test",
            base_reward={ResourceKind.ENERGY: 5.0},
        )
        affinity = niche.genome_affinity(g)
        assert affinity > 0.5

    def test_dominant_trait(self):
        g = Genome(curiosity=0.9, creativity=0.1, cooperation=0.1,
                   risk_tolerance=0.1, specialisation=0.1, resilience=0.1,
                   compassion=0.1, persistence=0.1)
        assert g.dominant_trait() == "curiosity"
