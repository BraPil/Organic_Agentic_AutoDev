"""
src/autoresearch/integration.py

Wiring helpers that attach the autoresearch engine to a running ecosystem.

The Body already has a ``_self_improvement_cycle`` stub (it records a fitness
history). ``attach_to_body`` upgrades that stub into a real autoresearch loop by
giving the Body an engine it delegates to — additively, without changing the
Body's existing behaviour when no engine is attached.

``build_engine`` is a convenience factory wiring an engine to the standard
evolution components.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from organic_agentic_autodev.autoresearch.evaluator import EcosystemEvaluator
from organic_agentic_autodev.autoresearch.proposer import Proposer
from organic_agentic_autodev.autoresearch.runner import AutoResearchEngine
from organic_agentic_autodev.utils.helpers import get_logger

if TYPE_CHECKING:
    from organic_agentic_autodev.evolution.mutator import Mutator
    from organic_agentic_autodev.evolution.selector import Selector
    from organic_agentic_autodev.organisms.body import Body

logger = get_logger("autoresearch.integration")


def build_engine(
    selector: "Selector | None" = None,
    mutator: "Mutator | None" = None,
    initial_energy: float = 1000.0,
    experiment_ticks: int = 8,
    rng: random.Random | None = None,
) -> AutoResearchEngine:
    """Construct an AutoResearchEngine wired to the given evolution components."""
    rng = rng or random.Random()
    evaluator = EcosystemEvaluator(initial_energy=initial_energy)
    proposer = Proposer(selector=selector, mutator=mutator, rng=rng)
    return AutoResearchEngine(
        evaluator=evaluator,
        proposer=proposer,
        selector=selector,
        mutator=mutator,
        experiment_ticks=experiment_ticks,
        rng=rng,
    )


def attach_to_body(body: "Body", engine: AutoResearchEngine) -> None:
    """
    Attach an engine to a Body so its self-improvement cycle runs real
    experiments. Idempotent and additive — Bodies without an engine are
    unaffected.
    """
    setattr(body, "_autoresearch_engine", engine)
    logger.info("Autoresearch engine attached to Body '%s'", body.name)
