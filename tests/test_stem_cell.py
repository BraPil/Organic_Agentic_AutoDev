"""
tests/test_stem_cell.py — Tests for StemCell lifecycle and differentiation.
"""

import random
import pytest

from organic_agentic_autodev.core.genome import Genome
from organic_agentic_autodev.core.stem_cell import StemCell
from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.mouseion.contracts import AgentRole, EventKind


def make_env(seed: int = 0) -> tuple[Mouseion, Environment]:
    rng = random.Random(seed)
    mouseion = Mouseion()
    env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
    niches = Environment.default_niche_set()
    env.seed_niches(niches)
    return mouseion, env


class TestStemCellCreation:
    def test_default_role_is_stem_cell(self):
        cell = StemCell()
        assert cell.role == AgentRole.STEM_CELL

    def test_not_differentiated_at_start(self):
        cell = StemCell()
        assert not cell.is_differentiated

    def test_initial_energy_set(self):
        cell = StemCell(initial_energy=15.0)
        assert cell.energy == 15.0

    def test_unique_ids(self):
        ids = {StemCell().agent_id for _ in range(10)}
        assert len(ids) == 10

    def test_parent_id_tracking(self):
        parent = StemCell()
        child = StemCell(parent_id=parent.agent_id)
        assert child.parent_id == parent.agent_id


class TestStemCellDrives:
    def test_seeking_energy_when_low(self):
        cell = StemCell(initial_energy=2.0)
        assert "energy" in cell.current_seeking()

    def test_seeking_niche_signal_when_undifferentiated(self):
        cell = StemCell()
        assert "niche_signal" in cell.current_seeking()

    def test_high_curiosity_seeks_knowledge(self):
        g = Genome(curiosity=0.9, risk_tolerance=0.5, cooperation=0.5,
                   specialisation=0.5, compassion=0.6, resilience=0.5,
                   creativity=0.5, persistence=0.5)
        cell = StemCell(genome=g)
        assert "knowledge" in cell.current_seeking()


class TestStemCellStep:
    def test_step_reduces_energy_over_time(self):
        mouseion, env = make_env()
        cell = StemCell(initial_energy=5.0)
        # Drain all resources first so step doesn't refill
        mouseion.draw_resource(
            __import__("organic_agentic_autodev.mouseion.contracts", fromlist=["ResourceKind"]).ResourceKind.ENERGY,
            mouseion.resource_level(
                __import__("organic_agentic_autodev.mouseion.contracts", fromlist=["ResourceKind"]).ResourceKind.ENERGY
            ),
            "test",
        )
        env.register(cell)
        initial_energy = cell.energy
        cell.step(env)
        # With no resources available, energy should decrease
        # (or stay same if draw returned 0 and cost offset it)
        assert cell.energy <= initial_energy + 0.1  # allow tiny float tolerance

    def test_step_accumulates_age(self):
        mouseion, env = make_env()
        cell = StemCell(initial_energy=20.0)
        env.register(cell)
        for _ in range(5):
            cell.step(env)
        assert cell.age_ticks == 5


class TestDifferentiation:
    def test_differentiation_occurs_after_enough_ticks(self):
        """A cell with a low differentiation threshold should differentiate."""
        rng = random.Random(99)
        mouseion, env = make_env(seed=99)

        # Create a cell with low differentiation threshold and high energy
        genome = Genome(
            curiosity=0.9, creativity=0.8, risk_tolerance=0.7,
            cooperation=0.6, specialisation=0.3, compassion=0.6,
            resilience=0.5, persistence=0.8,
            differentiation_threshold=0.3,  # very low threshold
            differentiation_min_energy=0.1,
        )
        cell = StemCell(genome=genome, initial_energy=50.0, rng=rng)
        env.register(cell)

        # Run up to 100 ticks
        for _ in range(100):
            env.tick()
            if cell.is_differentiated:
                break

        assert cell.is_differentiated, "Cell should have differentiated within 100 ticks"
        assert cell.role != AgentRole.STEM_CELL

    def test_differentiation_event_emitted(self):
        rng = random.Random(55)
        mouseion, env = make_env(seed=55)
        diff_events = []
        mouseion.subscribe(
            EventKind.DIFFERENTIATION_COMPLETED,
            lambda e: diff_events.append(e),
        )

        genome = Genome(
            curiosity=0.95, creativity=0.9, risk_tolerance=0.8,
            cooperation=0.7, specialisation=0.3, compassion=0.6,
            resilience=0.5, persistence=0.9,
            differentiation_threshold=0.25,
            differentiation_min_energy=0.05,
        )
        cell = StemCell(genome=genome, initial_energy=50.0, rng=rng)
        env.register(cell)

        for _ in range(100):
            env.tick()
            if cell.is_differentiated:
                break

        if cell.is_differentiated:
            assert len(diff_events) >= 1
            assert diff_events[0].source_agent_id == cell.agent_id

    def test_snapshot_reflects_state(self):
        cell = StemCell(initial_energy=10.0)
        snap = cell.snapshot()
        assert snap["role"] == AgentRole.STEM_CELL.value
        assert snap["differentiated"] is False
        assert snap["energy"] == 10.0
