"""
tests/test_autoresearch_cognition.py

Phase 3 (slice 1) — LLM cognition inside autoresearch proposals. Cognition is
advisory (chooses order + rationale); the Proposer keeps all value bounds and the
compassion guard. All offline; the LLM path is exercised with a stub provider.
"""

from __future__ import annotations

import random

from organic_agentic_autodev.autoresearch import (
    HeuristicProposalCognition,
    LLMProposalCognition,
    ProposalCognition,
    ProposalGuidance,
    Proposer,
)
from organic_agentic_autodev.autoresearch.contracts import ExperimentType
from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.mouseion.substrate import Mouseion


def _env() -> Environment:
    return Environment(mouseion=Mouseion(), rng=random.Random(1))


class _StubProvider:
    """Returns a fixed string for any prompt — no network."""

    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, system: str, prompt: str) -> str:
        return self._text


class _FixedCognition(ProposalCognition):
    """Forces a specific ordering / direction / rationale, for Proposer wiring."""

    name = "fixed"

    def __init__(
        self,
        order: list[ExperimentType],
        rationale: str = "",
        directions: dict[ExperimentType, str] | None = None,
    ) -> None:
        self._order = order
        self._rationale = rationale
        self._directions = directions or {}

    def guide(self, *, available_types, context):
        return ProposalGuidance(
            ordered_types=list(self._order),
            directions=dict(self._directions),
            rationale=self._rationale,
        )


# ---------------------------------------------------------------------------
# Default + heuristic
# ---------------------------------------------------------------------------

def test_default_cognition_is_heuristic():
    assert Proposer()._cognition.name == "heuristic"


def test_heuristic_returns_all_available_types():
    cog = HeuristicProposalCognition(random.Random(0))
    available = list(ExperimentType)
    guidance = cog.guide(available_types=available, context={})
    assert set(guidance.ordered_types) == set(available)
    assert guidance.rationale == ""


# ---------------------------------------------------------------------------
# LLM cognition (stub provider — offline)
# ---------------------------------------------------------------------------

def test_llm_cognition_parses_ranking_and_rationale():
    provider = _StubProvider(
        '{"ranking": ["energy_regen", "mutation_rate"], "rationale": "energy is low"}'
    )
    cog = LLMProposalCognition(provider=provider)
    guidance = cog.guide(
        available_types=[ExperimentType.MUTATION_RATE, ExperimentType.ENERGY_REGEN],
        context={},
    )
    assert guidance.ordered_types[0] == ExperimentType.ENERGY_REGEN
    assert guidance.rationale == "energy is low"


def test_llm_cognition_drops_invalid_types():
    provider = _StubProvider('{"ranking": ["energy_regen", "bogus"], "rationale": ""}')
    cog = LLMProposalCognition(provider=provider)
    guidance = cog.guide(
        available_types=[ExperimentType.ENERGY_REGEN, ExperimentType.MUTATION_RATE],
        context={},
    )
    assert guidance.ordered_types == [ExperimentType.ENERGY_REGEN]


def test_llm_cognition_falls_back_on_garbage():
    cog = LLMProposalCognition(provider=_StubProvider("not json at all"), rng=random.Random(0))
    available = list(ExperimentType)
    guidance = cog.guide(available_types=available, context={})
    # Fallback heuristic still returns every available type.
    assert set(guidance.ordered_types) == set(available)


# ---------------------------------------------------------------------------
# Proposer wiring — cognition is advisory, guard stays in code
# ---------------------------------------------------------------------------

def test_proposer_honors_cognition_order():
    p = Proposer(rng=random.Random(0), cognition=_FixedCognition([ExperimentType.ENERGY_REGEN]))
    built = p.propose(_env())
    assert built is not None
    proposal, _ = built
    assert proposal.experiment_type == ExperimentType.ENERGY_REGEN


def test_proposer_applies_cognition_rationale():
    p = Proposer(
        rng=random.Random(0),
        cognition=_FixedCognition([ExperimentType.ENERGY_REGEN], "energy headroom is low"),
    )
    proposal, _ = p.propose(_env())
    assert proposal.rationale == "energy headroom is low"


def test_proposer_still_proposes_when_cognition_empty():
    # Empty guidance → Proposer falls back to trying every available type.
    p = Proposer(rng=random.Random(0), cognition=_FixedCognition([]))
    assert p.propose(_env()) is not None


def test_cognition_cannot_bypass_compassion_guard():
    # Even if cognition prioritizes it, an out-of-bounds value can never ship:
    # the guard lives in the Proposer, not the cognition.
    p = Proposer(rng=random.Random(0), cognition=_FixedCognition([ExperimentType.ENERGY_REGEN]))
    proposal, _ = p.propose(_env())
    ok, _reason = p.passes_compassion_guard(proposal)
    assert ok


# ---------------------------------------------------------------------------
# Direction (P3.2) — cognition picks the way, code keeps the bounds
# ---------------------------------------------------------------------------

def test_llm_cognition_parses_directions_and_drops_invalid():
    provider = _StubProvider(
        '{"ranking": ["energy_regen"], '
        '"directions": {"energy_regen": "increase", "mutation_rate": "sideways"}, '
        '"rationale": ""}'
    )
    cog = LLMProposalCognition(provider=provider)
    guidance = cog.guide(
        available_types=[ExperimentType.ENERGY_REGEN, ExperimentType.MUTATION_RATE],
        context={},
    )
    assert guidance.directions == {ExperimentType.ENERGY_REGEN: "increase"}


def test_proposer_honors_increase_direction():
    p = Proposer(
        rng=random.Random(0),
        cognition=_FixedCognition(
            [ExperimentType.ENERGY_REGEN],
            directions={ExperimentType.ENERGY_REGEN: "increase"},
        ),
    )
    proposal, _ = p.propose(_env())
    assert proposal.new_value > proposal.old_value


def test_proposer_honors_decrease_direction():
    p = Proposer(
        rng=random.Random(0),
        cognition=_FixedCognition(
            [ExperimentType.ENERGY_REGEN],
            directions={ExperimentType.ENERGY_REGEN: "decrease"},
        ),
    )
    proposal, _ = p.propose(_env())
    assert proposal.new_value < proposal.old_value


def test_invalid_direction_falls_back_to_a_valid_proposal():
    # An unrecognized direction is ignored (random fallback), never an error.
    p = Proposer(
        rng=random.Random(0),
        cognition=_FixedCognition(
            [ExperimentType.ENERGY_REGEN],
            directions={ExperimentType.ENERGY_REGEN: "sideways"},
        ),
    )
    built = p.propose(_env())
    assert built is not None
    assert built[0].experiment_type == ExperimentType.ENERGY_REGEN


def test_context_includes_ecosystem_signals():
    p = Proposer()
    ctx = p._context(_env(), set())
    assert "energy_level" in ctx
    assert "agent_count" in ctx
