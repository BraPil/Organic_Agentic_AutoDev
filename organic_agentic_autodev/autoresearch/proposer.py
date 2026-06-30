"""
src/autoresearch/proposer.py

Proposer + Checkpointer for autoresearch experiments.

The Proposer reads the current ecosystem parameters and proposes a single,
bounded perturbation to test. It consults experiment history to avoid repeating
recently-failed proposals, and applies a compassion guard that rejects changes
which would plausibly harm agents (e.g. starving the energy pool, or cranking
selection pressure to lethal levels).

The Checkpointer captures only the parameter under test (not the whole
ecosystem), so apply/revert is fast and non-destructive.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from organic_agentic_autodev.autoresearch.cognition import (
    HeuristicProposalCognition,
    ProposalCognition,
)
from organic_agentic_autodev.autoresearch.contracts import ExperimentProposalV0, ExperimentType
from organic_agentic_autodev.mouseion.contracts import ResourceKind
from organic_agentic_autodev.utils.helpers import clamp, get_logger, new_id

if TYPE_CHECKING:
    from organic_agentic_autodev.core.environment import Environment
    from organic_agentic_autodev.evolution.mutator import Mutator
    from organic_agentic_autodev.evolution.selector import Selector

logger = get_logger("autoresearch.proposer")

# Hard floors below which a change is considered harmful (compassion guard).
_MIN_ENERGY_REGEN = 0.005          # never starve the pool
_MAX_SELECTION_STRENGTH = 0.6      # never make selection lethal
_MAX_MUTATION_RATE = 0.25          # never destabilise the gene pool


class Checkpointer:
    """Snapshot and restore a single experiment target parameter."""

    def __init__(self) -> None:
        self._getter: Callable[[], float] | None = None
        self._setter: Callable[[float], None] | None = None
        self._saved: float | None = None

    def bind(self, getter: Callable[[], float], setter: Callable[[float], None]) -> None:
        self._getter = getter
        self._setter = setter

    def snapshot(self) -> float:
        assert self._getter is not None
        self._saved = self._getter()
        return self._saved

    def apply(self, value: float) -> None:
        assert self._setter is not None
        self._setter(value)

    def restore(self) -> None:
        if self._setter is not None and self._saved is not None:
            self._setter(self._saved)


class Proposer:
    """Generates bounded, guarded experiment proposals."""

    def __init__(
        self,
        selector: Selector | None = None,
        mutator: Mutator | None = None,
        rng: random.Random | None = None,
        cognition: ProposalCognition | None = None,
    ) -> None:
        self._selector = selector
        self._mutator = mutator
        self.rng = rng or random.Random()
        # Strategy (which experiment, in what order) is delegated; mechanics and
        # the compassion guard stay here. Default heuristic shares the RNG, so
        # behaviour stays deterministic and reproducible.
        self._cognition = cognition or HeuristicProposalCognition(self.rng)

    # ------------------------------------------------------------------
    # Proposal generation
    # ------------------------------------------------------------------

    def available_types(self) -> list[ExperimentType]:
        """Experiment types that are wired up given the provided components."""
        types = [ExperimentType.NICHE_URGENCY_GROWTH, ExperimentType.ENERGY_REGEN]
        if self._selector is not None:
            types += [ExperimentType.CARRYING_CAPACITY, ExperimentType.SELECTION_STRENGTH]
        if self._mutator is not None:
            types.append(ExperimentType.MUTATION_RATE)
        return types

    def propose(
        self,
        env: Environment,
        recent_failures: set[str] | None = None,
    ) -> tuple[ExperimentProposalV0, Checkpointer] | None:
        """
        Propose one experiment. Returns (proposal, bound checkpointer) or None if
        nothing viable / all candidates fail the compassion guard.
        """
        recent_failures = recent_failures or set()
        types = [t for t in self.available_types() if t.value not in recent_failures]
        if not types:
            types = self.available_types()

        # Cognition decides the order to try (and may supply a rationale); it is
        # advisory. We honor its preference but guarantee every available type is
        # still tried and no invalid type is injected.
        guidance = self._cognition.guide(
            available_types=types, context=self._context(env, recent_failures)
        )
        preferred = [t for t in guidance.ordered_types if t in types]
        ordered = preferred + [t for t in types if t not in preferred]

        for etype in ordered:
            built = self._build(
                etype,
                env,
                override_rationale=guidance.rationale or None,
                direction=guidance.directions.get(etype),
            )
            if built is None:
                continue
            proposal, checkpointer = built
            ok, reason = self.passes_compassion_guard(proposal)
            if ok:
                return proposal, checkpointer
            logger.info("Compassion guard rejected %s: %s", etype.value, reason)
        return None

    def _context(
        self, env: Environment, recent_failures: set[str]
    ) -> dict[str, object]:
        """Snapshot of ecosystem state a cognition may reason over (read-only)."""
        return {
            "agent_count": len(env.all_agents()),
            "open_niches": len(env.open_niches()),
            "energy_level": round(env.mouseion.resource_level(ResourceKind.ENERGY), 2),
            "available_experiments": [t.value for t in self.available_types()],
            "recently_failed": sorted(recent_failures),
        }

    def _build(
        self,
        etype: ExperimentType,
        env: Environment,
        *,
        override_rationale: str | None = None,
        direction: str | None = None,
    ) -> tuple[ExperimentProposalV0, Checkpointer] | None:
        cp = Checkpointer()

        def rationale(default: str) -> str:
            return override_rationale or default

        def pick(down: float, up: float) -> float:
            """Resolve the perturbation. Cognition picks the *direction*; the two
            magnitudes (and the downstream clamp + guard) are fixed in code. With
            no/invalid hint, fall back to a random direction — the heuristic
            default, which keeps the RNG sequence (and existing tests) unchanged.
            """
            if direction == "increase":
                return up
            if direction == "decrease":
                return down
            return self.rng.choice([down, up])

        if etype == ExperimentType.ENERGY_REGEN:
            cp.bind(lambda: env.resource_regen_rate,
                    lambda v: setattr(env, "resource_regen_rate", v))
            old = cp.snapshot()
            new = clamp(old * pick(0.7, 1.4), 0.0, 0.2)
            return self._mk(etype, "global", old, new,
                            rationale("tune resource regeneration")), cp

        if etype == ExperimentType.NICHE_URGENCY_GROWTH:
            open_niches = env.open_niches()
            if not open_niches:
                return None
            niche = self.rng.choice(open_niches)
            cp.bind(lambda: niche.urgency_growth_rate,
                    lambda v: setattr(niche, "urgency_growth_rate", v))
            old = cp.snapshot()
            new = clamp(old * pick(0.6, 1.5), 0.0, 0.1)
            return self._mk(etype, niche.niche_id, old, new,
                            rationale("tune niche urgency growth")), cp

        if etype == ExperimentType.CARRYING_CAPACITY and self._selector is not None:
            sel = self._selector
            cp.bind(lambda: float(sel.carrying_capacity),
                    lambda v: setattr(sel, "carrying_capacity", int(v)))
            old = cp.snapshot()
            new = max(2.0, old + pick(-5.0, 5.0))
            return self._mk(etype, "global", old, new,
                            rationale("tune population carrying capacity")), cp

        if etype == ExperimentType.SELECTION_STRENGTH and self._selector is not None:
            sel = self._selector
            cp.bind(lambda: sel.selection_strength,
                    lambda v: setattr(sel, "selection_strength", v))
            old = cp.snapshot()
            new = clamp(old + pick(-0.1, 0.1), 0.0, 1.0)
            return self._mk(etype, "global", old, new,
                            rationale("tune selection strength")), cp

        if etype == ExperimentType.MUTATION_RATE and self._mutator is not None:
            mut = self._mutator
            cp.bind(lambda: mut.base_rate,
                    lambda v: setattr(mut, "base_rate", v))
            old = cp.snapshot()
            new = clamp(old + pick(-0.02, 0.02), 0.001, 0.5)
            return self._mk(etype, "global", old, new,
                            rationale("tune genome mutation rate")), cp

        return None

    def _mk(self, etype, target, old, new, rationale) -> ExperimentProposalV0:
        return ExperimentProposalV0(
            experiment_id=new_id("exp_"),
            experiment_type=etype,
            target=target,
            old_value=round(float(old), 5),
            new_value=round(float(new), 5),
            rationale=rationale,
        )

    # ------------------------------------------------------------------
    # Compassion guard
    # ------------------------------------------------------------------

    def passes_compassion_guard(self, proposal: ExperimentProposalV0) -> tuple[bool, str]:
        """
        Reject proposals that would plausibly harm agents — compassion is a
        first-class architectural value, not a post-hoc filter.
        """
        t, v = proposal.experiment_type, proposal.new_value
        if t == ExperimentType.ENERGY_REGEN and v < _MIN_ENERGY_REGEN:
            return False, f"energy regen {v:.4f} < floor {_MIN_ENERGY_REGEN} (would starve agents)"
        if t == ExperimentType.SELECTION_STRENGTH and v > _MAX_SELECTION_STRENGTH:
            return False, f"selection strength {v:.2f} > cap {_MAX_SELECTION_STRENGTH} (lethal)"
        if t == ExperimentType.MUTATION_RATE and v > _MAX_MUTATION_RATE:
            return False, f"mutation rate {v:.2f} > cap {_MAX_MUTATION_RATE} (destabilising)"
        if t == ExperimentType.CARRYING_CAPACITY and v < 2:
            return False, "carrying capacity < 2 (population collapse)"
        return True, ""
