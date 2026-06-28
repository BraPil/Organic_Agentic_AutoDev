"""
tests/test_organism_hierarchy.py — Tests for Cell, Organ, and Body.
"""

import random
import pytest

from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.mouseion.contracts import AgentRole
from organic_agentic_autodev.organisms.cell import Cell, COMPATIBLE_ROLES
from organic_agentic_autodev.organisms.organ import Organ, MIN_ORGAN_SIZE
from organic_agentic_autodev.organisms.body import Body
from organic_agentic_autodev.slime_mold.network import SlimeMoldNetwork
from organic_agentic_autodev.core.genome import Genome


def make_env(seed: int = 0) -> tuple[Mouseion, Environment]:
    rng = random.Random(seed)
    mouseion = Mouseion()
    env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
    env.seed_niches(Environment.default_niche_set())
    return mouseion, env


class TestCell:
    def test_cell_role_is_set(self):
        cell = Cell(role=AgentRole.RESEARCHER)
        assert cell.role == AgentRole.RESEARCHER

    def test_cell_is_differentiated(self):
        cell = Cell(role=AgentRole.CODER)
        assert cell.is_differentiated is True

    def test_specialisation_score_increases(self):
        mouseion, env = make_env()
        cell = Cell(role=AgentRole.RESEARCHER, initial_energy=30.0)
        env.register(cell)
        initial_spec = cell.specialisation_score
        for _ in range(10):
            cell.step(env)
        assert cell.specialisation_score >= initial_spec

    def test_cell_joins_organ(self):
        cell = Cell(role=AgentRole.RESEARCHER)
        cell.join_organ("org_123")
        assert cell.organ_id == "org_123"

    def test_cell_leaves_organ(self):
        cell = Cell(role=AgentRole.SYNTHESIZER)
        cell.join_organ("org_456")
        cell.leave_organ()
        assert cell.organ_id is None

    def test_compatible_roles_defined(self):
        for role in AgentRole:
            if role != AgentRole.STEM_CELL:
                assert role in COMPATIBLE_ROLES, f"{role} missing from COMPATIBLE_ROLES"

    def test_cell_attaches_to_network(self):
        net = SlimeMoldNetwork(rng=random.Random(0))
        cell = Cell(role=AgentRole.CONNECTOR)
        cell.attach_to_network(net)
        assert net._pathfinder._graph.has_node(cell.agent_id)


class TestOrgan:
    def _make_cells(self, role: AgentRole, n: int) -> list[Cell]:
        return [Cell(role=role, initial_energy=10.0) for _ in range(n)]

    def test_organ_forms_with_min_cells(self):
        cells = self._make_cells(AgentRole.RESEARCHER, MIN_ORGAN_SIZE)
        organ = Organ(founding_cells=cells)
        assert organ.is_viable

    def test_organ_below_min_not_viable(self):
        cells = self._make_cells(AgentRole.RESEARCHER, MIN_ORGAN_SIZE - 1)
        organ = Organ(founding_cells=cells)
        assert not organ.is_viable

    def test_dominant_role_matches_majority(self):
        researchers = self._make_cells(AgentRole.RESEARCHER, 3)
        coders = self._make_cells(AgentRole.CODER, 1)
        organ = Organ(founding_cells=researchers + coders)
        assert organ.dominant_role == AgentRole.RESEARCHER

    def test_add_cell_increases_size(self):
        cells = self._make_cells(AgentRole.SYNTHESIZER, 2)
        organ = Organ(founding_cells=cells)
        new_cell = Cell(role=AgentRole.SYNTHESIZER, initial_energy=10.0)
        organ.add_cell(new_cell)
        assert organ.size == 3

    def test_remove_cell_decreases_size(self):
        cells = self._make_cells(AgentRole.CODER, 3)
        organ = Organ(founding_cells=cells)
        organ.remove_cell(cells[0].agent_id)
        assert organ.size == 2

    def test_step_returns_summary(self):
        mouseion, env = make_env()
        cells = [Cell(role=AgentRole.RESEARCHER, initial_energy=15.0) for _ in range(3)]
        for c in cells:
            env.register(c)
        organ = Organ(founding_cells=cells)
        result = organ.step(env)
        assert "organ_id" in result
        assert "cells" in result

    def test_snapshot_contains_key_fields(self):
        cells = self._make_cells(AgentRole.GUARDIAN, 2)
        organ = Organ(founding_cells=cells)
        snap = organ.snapshot()
        assert snap["size"] == 2
        assert "dominant_role" in snap
        assert "mean_energy" in snap


class TestBody:
    def test_body_not_functional_with_few_organs(self):
        body = Body("TestBody")
        from organic_agentic_autodev.organisms.organ import MIN_ORGAN_SIZE
        for _ in range(2):  # fewer than MIN_ORGANS_FOR_FULL_FUNCTION
            cells = [Cell(role=AgentRole.RESEARCHER, initial_energy=10.0) for _ in range(2)]
            organ = Organ(founding_cells=cells)
            body.register_organ(organ)
        assert not body.is_fully_functional

    def test_body_becomes_functional_with_enough_organs(self):
        body = Body("FullBody")
        from organic_agentic_autodev.organisms.body import MIN_ORGANS_FOR_FULL_FUNCTION
        for i in range(MIN_ORGANS_FOR_FULL_FUNCTION):
            role = list(AgentRole)[i + 1]  # skip STEM_CELL
            cells = [Cell(role=role, initial_energy=10.0) for _ in range(2)]
            organ = Organ(founding_cells=cells)
            body.register_organ(organ)
        assert body.is_fully_functional

    def test_body_step_returns_summary(self):
        mouseion, env = make_env()
        body = Body("StepBody")
        cells = [Cell(role=AgentRole.SYNTHESIZER, initial_energy=10.0) for _ in range(2)]
        for c in cells:
            env.register(c)
        organ = Organ(founding_cells=cells)
        body.register_organ(organ)
        result = body.step(env)
        assert "body_id" in result
        assert "organs" in result

    def test_body_goals_tracked(self):
        body = Body("GoalBody")
        body.set_goal("Achieve enlightened synthesis")
        assert "Achieve enlightened synthesis" in body._current_goals

    def test_body_snapshot_structure(self):
        body = Body("SnapBody")
        snap = body.snapshot()
        assert "body_id" in snap
        assert "fully_functional" in snap
        assert "organs" in snap
        assert "visions_count" in snap
