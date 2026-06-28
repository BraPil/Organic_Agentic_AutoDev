"""
tests/test_autoresearch.py

Tests for the autoresearch self-improvement loop.

Deterministic and offline. Commit/rollback behaviour is tested with a scripted
evaluator so the decision is unambiguous, and the compassion guard is tested
directly against crafted proposals.
"""

from __future__ import annotations

import random

import pytest

from src.autoresearch import (
    AutoResearchEngine,
    Checkpointer,
    EcosystemEvaluator,
    Proposer,
    attach_to_body,
    build_engine,
)
from src.autoresearch.contracts import ExperimentProposalV0, ExperimentType
from src.core.environment import Environment
from src.evolution.mutator import Mutator
from src.evolution.selector import Selector
from src.mouseion.substrate import Mouseion
from src.organisms.body import Body
from src.utils.helpers import new_id


@pytest.fixture
def env():
    m = Mouseion()
    e = Environment(mouseion=m, rng=random.Random(1))
    e.seed_niches(Environment.default_niche_set())
    return e


def _proposal(etype: ExperimentType, new_value: float) -> ExperimentProposalV0:
    return ExperimentProposalV0(
        experiment_id=new_id("exp_"),
        experiment_type=etype,
        target="global",
        old_value=0.05,
        new_value=new_value,
    )


# ---------------------------------------------------------------------------
# Checkpointer
# ---------------------------------------------------------------------------

def test_checkpointer_restores_exact_value():
    store = {"v": 0.05}
    cp = Checkpointer()
    cp.bind(lambda: store["v"], lambda x: store.__setitem__("v", x))
    saved = cp.snapshot()
    cp.apply(0.99)
    assert store["v"] == 0.99
    cp.restore()
    assert store["v"] == saved == 0.05


# ---------------------------------------------------------------------------
# Compassion guard
# ---------------------------------------------------------------------------

def test_guard_rejects_starvation():
    p = Proposer()
    ok, reason = p.passes_compassion_guard(_proposal(ExperimentType.ENERGY_REGEN, 0.0001))
    assert not ok
    assert "starve" in reason.lower()


def test_guard_rejects_lethal_selection():
    p = Proposer()
    ok, _ = p.passes_compassion_guard(_proposal(ExperimentType.SELECTION_STRENGTH, 0.95))
    assert not ok


def test_guard_rejects_destabilising_mutation():
    p = Proposer()
    ok, _ = p.passes_compassion_guard(_proposal(ExperimentType.MUTATION_RATE, 0.5))
    assert not ok


def test_guard_allows_safe_change():
    p = Proposer()
    ok, _ = p.passes_compassion_guard(_proposal(ExperimentType.ENERGY_REGEN, 0.04))
    assert ok


# ---------------------------------------------------------------------------
# Proposer
# ---------------------------------------------------------------------------

def test_proposer_produces_valid_proposal(env):
    p = Proposer(rng=random.Random(3))
    built = p.propose(env)
    assert built is not None
    proposal, cp = built
    assert proposal.experiment_type in ExperimentType
    assert isinstance(proposal.new_value, float)


def test_proposer_available_types_grow_with_components():
    base = Proposer()
    full = Proposer(selector=Selector(), mutator=Mutator())
    assert len(full.available_types()) > len(base.available_types())


def test_proposer_proposal_passes_its_own_guard(env):
    p = Proposer(selector=Selector(), mutator=Mutator(), rng=random.Random(7))
    for _ in range(10):
        built = p.propose(env)
        if built is None:
            continue
        proposal, _ = built
        ok, _r = p.passes_compassion_guard(proposal)
        assert ok  # propose() must only return guard-passing proposals


# ---------------------------------------------------------------------------
# Engine commit / rollback (scripted evaluator)
# ---------------------------------------------------------------------------

class _ScriptedEvaluator(EcosystemEvaluator):
    """Returns a fixed sequence of scores so commit/revert is deterministic."""
    def __init__(self, scores):
        super().__init__()
        self._scores = list(scores)
        self._i = 0

    def score(self, env):
        v = self._scores[min(self._i, len(self._scores) - 1)]
        self._i += 1
        return v

    def reset_baseline(self, env):
        pass


def test_engine_commits_improvement(env):
    # baseline window averages 0.2, result window averages 0.8 → commit.
    evaluator = _ScriptedEvaluator([0.2] * 8 + [0.8] * 8)
    engine = AutoResearchEngine(evaluator=evaluator, experiment_ticks=8,
                                step_fn=lambda: None, rng=random.Random(5))
    cycle = engine.run_cycle(env)
    assert cycle.result is not None
    assert cycle.result.committed is True
    assert cycle.result.delta > 0


def test_engine_reverts_regression(env):
    # baseline window 0.8, result window 0.2 → revert.
    evaluator = _ScriptedEvaluator([0.8] * 8 + [0.2] * 8)
    engine = AutoResearchEngine(evaluator=evaluator, experiment_ticks=8,
                                step_fn=lambda: None, rng=random.Random(2))
    cycle = engine.run_cycle(env)
    assert cycle.result is not None
    assert cycle.result.committed is False
    assert cycle.result.delta < 0


def test_engine_reverts_parameter_to_original(env):
    """After a reverted experiment, the targeted parameter is exactly restored."""
    regen_before = env.resource_regen_rate
    # Force an ENERGY_REGEN proposal by giving only that component, regression scores.
    proposer = Proposer(rng=random.Random(0))
    engine = AutoResearchEngine(
        evaluator=_ScriptedEvaluator([0.9] * 6 + [0.1] * 6),
        proposer=proposer, experiment_ticks=6, step_fn=lambda: None,
        rng=random.Random(0),
    )
    cycle = engine.run_cycle(env)
    if cycle.proposal and cycle.proposal.experiment_type == ExperimentType.ENERGY_REGEN:
        assert not cycle.result.committed
        assert env.resource_regen_rate == regen_before


def test_engine_records_to_mouseion(env):
    evaluator = _ScriptedEvaluator([0.2] * 8 + [0.8] * 8)
    engine = AutoResearchEngine(evaluator=evaluator, experiment_ticks=8,
                                step_fn=lambda: None, rng=random.Random(5))
    before = len(env.mouseion.query_knowledge("autoresearch"))
    engine.run_cycle(env)
    after = len(env.mouseion.query_knowledge("autoresearch"))
    assert after == before + 1


def test_engine_summary(env):
    evaluator = _ScriptedEvaluator([0.5] * 100)
    engine = AutoResearchEngine(evaluator=evaluator, experiment_ticks=4,
                                step_fn=lambda: None, rng=random.Random(9))
    for _ in range(3):
        engine.run_cycle(env)
    s = engine.summary()
    assert s["cycles"] == 3
    assert s["committed"] + s["reverted"] + s["no_proposal"] == 3


# ---------------------------------------------------------------------------
# Integration with Body
# ---------------------------------------------------------------------------

def test_build_engine_factory():
    engine = build_engine(selector=Selector(), mutator=Mutator())
    assert isinstance(engine, AutoResearchEngine)


def test_attach_to_body_runs_real_cycles(env):
    """A Body with an attached engine runs experiments in its improvement cycle."""
    from src.organisms.cell import Cell
    from src.organisms.organ import Organ
    from src.mouseion.contracts import AgentRole

    body = Body("Test Body")
    # Give the body an organ so _self_improvement_cycle proceeds.
    cells = [Cell(role=AgentRole.RESEARCHER, initial_energy=15.0) for _ in range(2)]
    body.register_organ(Organ(founding_cells=cells))

    engine = build_engine(rng=random.Random(4))
    attach_to_body(body, engine)

    # Drive the body far enough to trigger a self-improvement cycle (every 20 ticks).
    for _ in range(20):
        body.step(env)
    assert engine.summary()["cycles"] >= 1


def test_body_without_engine_still_works(env):
    """Backwards compatibility: a Body with no engine behaves as before."""
    from src.organisms.cell import Cell
    from src.organisms.organ import Organ
    from src.mouseion.contracts import AgentRole

    body = Body("Plain Body")
    cells = [Cell(role=AgentRole.RESEARCHER, initial_energy=15.0) for _ in range(2)]
    body.register_organ(Organ(founding_cells=cells))
    for _ in range(20):
        body.step(env)
    # No crash, and improvement history recorded by the original code path.
    assert len(body._improvement_history) >= 1
