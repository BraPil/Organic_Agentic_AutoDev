"""
src/autoresearch/runner.py

AutoResearchEngine — the fixed-budget experiment loop.

One cycle:
  1. Propose a single guarded parameter change.
  2. Measure baseline ecosystem fitness over a short window (old value).
  3. Apply the change; measure fitness over an equal window (new value).
  4. Commit if it improved beyond a threshold, else roll back.
  5. Record the full ImprovementCycleV0 in the Mouseion for provenance.

The measurement runs the ecosystem via a pluggable ``step_fn`` (default
``env.tick``), averaging the ecosystem score across the window so the decision
is robust to single-tick noise. This is karpathy/autoresearch applied to agent
*behaviour parameters* rather than model weights.
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING

from organic_agentic_autodev.autoresearch.contracts import (
    ExperimentResultV0,
    ImprovementCycleV0,
)
from organic_agentic_autodev.autoresearch.evaluator import EcosystemEvaluator
from organic_agentic_autodev.autoresearch.proposer import Proposer
from organic_agentic_autodev.utils.helpers import get_logger, new_id

if TYPE_CHECKING:
    from organic_agentic_autodev.core.environment import Environment
    from organic_agentic_autodev.evolution.mutator import Mutator
    from organic_agentic_autodev.evolution.selector import Selector

logger = get_logger("autoresearch.runner")

# Minimum fitness gain required to keep a change.
IMPROVEMENT_THRESHOLD = 0.005


class AutoResearchEngine:
    """Runs autonomous, fixed-budget self-improvement experiments."""

    def __init__(
        self,
        evaluator: EcosystemEvaluator | None = None,
        proposer: Proposer | None = None,
        selector: Selector | None = None,
        mutator: Mutator | None = None,
        experiment_ticks: int = 8,
        step_fn: Callable[[], None] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.rng = rng or random.Random()
        self._evaluator = evaluator or EcosystemEvaluator()
        self._proposer = proposer or Proposer(selector=selector, mutator=mutator, rng=self.rng)
        self._experiment_ticks = experiment_ticks
        self._step_fn = step_fn
        self._recent_failures: deque[str] = deque(maxlen=4)
        self._history: list[ImprovementCycleV0] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_cycle(self, env: Environment) -> ImprovementCycleV0:
        """Run one propose → test → commit/rollback cycle."""
        step = self._step_fn or env.tick
        proposed = self._proposer.propose(
            env, set(self._recent_failures), context_extra=self._fitness_context()
        )

        if proposed is None:
            cycle = ImprovementCycleV0(
                cycle_id=new_id("cyc_"),
                tick=env.tick_count,
                notes={"status": "no_viable_proposal"},
            )
            self._history.append(cycle)
            return cycle

        proposal, checkpointer = proposed

        baseline = self._measure(env, step)
        checkpointer.apply(proposal.new_value)
        result_score = self._measure(env, step)
        delta = round(result_score - baseline, 5)

        committed = delta > IMPROVEMENT_THRESHOLD
        if not committed:
            checkpointer.restore()
            self._recent_failures.append(proposal.experiment_type.value)
            logger.info("Reverted %s (Δ=%+.4f)", proposal.experiment_type.value, delta)
        else:
            logger.info("Committed %s (Δ=%+.4f): %.4f → %.4f param",
                        proposal.experiment_type.value, delta,
                        proposal.old_value, proposal.new_value)

        result = ExperimentResultV0(
            experiment_id=proposal.experiment_id,
            baseline_score=round(baseline, 5),
            result_score=round(result_score, 5),
            delta=delta,
            committed=committed,
            ticks_run=self._experiment_ticks * 2,
        )
        cycle = ImprovementCycleV0(
            cycle_id=new_id("cyc_"),
            tick=env.tick_count,
            proposal=proposal,
            result=result,
        )
        self._history.append(cycle)
        self._record_to_mouseion(env, cycle)
        return cycle

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fitness_context(self) -> dict[str, object]:
        """
        Summarize the recent fitness trajectory for the proposal cognition. The
        runner owns the experiment history; the Proposer can't see it, so we hand
        it across as advisory context (the cognition may reason over it; the
        heuristic ignores it). Deterministic — derived from recorded deltas only.
        """
        deltas = [
            c.result.delta for c in self._history[-3:] if c.result is not None
        ]
        if not deltas:
            trend = "unknown"
        elif sum(deltas) > IMPROVEMENT_THRESHOLD:
            trend = "improving"
        elif sum(deltas) < -IMPROVEMENT_THRESHOLD:
            trend = "declining"
        else:
            trend = "flat"
        return {
            "fitness_trend": trend,
            "recent_fitness_deltas": [round(d, 4) for d in deltas],
        }

    def _measure(self, env: Environment, step: Callable[[], None]) -> float:
        """Average ecosystem score across the experiment window."""
        self._evaluator.reset_baseline(env)
        scores: list[float] = []
        for _ in range(self._experiment_ticks):
            step()
            scores.append(self._evaluator.score(env))
        return sum(scores) / len(scores) if scores else 0.0

    def _record_to_mouseion(self, env: Environment, cycle: ImprovementCycleV0) -> None:
        if cycle.result is None or cycle.proposal is None:
            return
        env.mouseion.store_knowledge(
            author_id="autoresearch_engine",
            content=(
                f"Experiment {cycle.proposal.experiment_type.value} on "
                f"{cycle.proposal.target}: {cycle.proposal.old_value} → "
                f"{cycle.proposal.new_value}; Δfitness={cycle.result.delta:+.4f}; "
                f"{'COMMITTED' if cycle.result.committed else 'reverted'}."
            ),
            topic_tags=["autoresearch", "self_improvement", "experiment"],
            confidence=0.6,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[ImprovementCycleV0]:
        return list(self._history)

    @property
    def committed_count(self) -> int:
        return sum(1 for c in self._history if c.result and c.result.committed)

    def summary(self) -> dict:
        run = [c for c in self._history if c.result is not None]
        return {
            "cycles": len(self._history),
            "experiments_run": len(run),
            "committed": self.committed_count,
            "reverted": sum(1 for c in run if not c.result.committed),
            "no_proposal": sum(1 for c in self._history if c.result is None),
        }
