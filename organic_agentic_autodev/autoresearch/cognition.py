"""
organic_agentic_autodev/autoresearch/cognition.py

The reasoning layer for autoresearch proposals (Phase 3 — cognition depth).

The Proposer owns the *mechanics* of an experiment — which parameter, the bounded
perturbation, and the compassion guard — all in code. A ``ProposalCognition``
owns the *strategy*: given the available experiment types and the ecosystem's
current state, in what order should they be tried, and why. The cognition is
**advisory** — it can reorder and explain, but every value bound and the
compassion guard stay in the Proposer, so cognition can never produce an unsafe
experiment (compassion-as-first-class is enforced structurally, not by trust).

Two implementations, mirroring the codebase's cognition pattern (abstract
interface + deterministic offline default + live LLM that degrades gracefully):

  - ``HeuristicProposalCognition`` — the offline default. Random ordering through
    the Proposer's seeded RNG, so runs stay reproducible. No reasoning, no network.
  - ``LLMProposalCognition`` — wraps a bridge ``CognitionProvider`` (Anthropic when
    keyed). Asks for a ranked ordering + a data-grounded rationale, and falls back
    to the heuristic on any failure, so a misbehaving model never blocks a proposal.
"""

from __future__ import annotations

import json
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from organic_agentic_autodev.autoresearch.contracts import ExperimentType
from organic_agentic_autodev.cognition.bridge import CognitionProvider, make_cognition
from organic_agentic_autodev.utils.helpers import get_logger, sanitize_text

logger = get_logger("autoresearch.cognition")


#: The only perturbation directions a cognition may request. The Proposer maps
#: these to bounded magnitudes; anything else is ignored (→ random direction).
VALID_DIRECTIONS = ("increase", "decrease")


@dataclass
class ProposalGuidance:
    """A cognition's advice: which experiment types to try, which way to nudge
    each, and why.

    ``ordered_types`` is a *preference*. The Proposer filters it to the actually
    available types and appends any the cognition omitted, so every option is
    still tried and no invalid type sneaks in. ``directions`` maps a type to
    ``"increase"``/``"decrease"`` — a *direction* hint only; the Proposer still
    owns the (bounded) magnitude and the compassion guard, and falls back to a
    random direction when no valid hint is given. ``rationale`` (when non-empty)
    replaces the experiment's canned rationale with a data-grounded one.
    """

    ordered_types: list[ExperimentType] = field(default_factory=list)
    directions: dict[ExperimentType, str] = field(default_factory=dict)
    rationale: str = ""


class ProposalCognition(ABC):
    """Decides the order in which experiment types are tried, and why."""

    name: str = "abstract"

    @abstractmethod
    def guide(
        self, *, available_types: list[ExperimentType], context: dict[str, Any]
    ) -> ProposalGuidance:
        raise NotImplementedError


class HeuristicProposalCognition(ProposalCognition):
    """Random ordering via a seeded RNG — the offline default. No reasoning."""

    name = "heuristic"

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()

    def guide(
        self, *, available_types: list[ExperimentType], context: dict[str, Any]
    ) -> ProposalGuidance:
        types = list(available_types)
        self.rng.shuffle(types)
        return ProposalGuidance(ordered_types=types, rationale="")


class LLMProposalCognition(ProposalCognition):
    """
    Ranking backed by a bridge ``CognitionProvider`` (Anthropic when keyed).

    The model is asked for a strict-JSON ranking + rationale. Any failure —
    transport error, unparseable output, empty ranking — falls back to the
    heuristic, so a proposal is never blocked by model behaviour.
    """

    name = "llm"

    def __init__(
        self,
        provider: CognitionProvider | None = None,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self._provider = provider or make_cognition()
        self._fallback = HeuristicProposalCognition(rng or random.Random())

    def guide(
        self, *, available_types: list[ExperimentType], context: dict[str, Any]
    ) -> ProposalGuidance:
        try:
            system, prompt = self._build_prompt(available_types, context)
            guidance = self._parse(self._provider.generate(system, prompt), available_types)
            if guidance.ordered_types:
                return guidance
            logger.info("LLM proposal cognition returned no ranking; heuristic fallback")
        except Exception as exc:  # noqa: BLE001 — cognition must never block a proposal
            logger.warning("LLM proposal cognition failed (%s); heuristic fallback", exc)
        return self._fallback.guide(available_types=available_types, context=context)

    @staticmethod
    def _build_prompt(
        available_types: list[ExperimentType], context: dict[str, Any]
    ) -> tuple[str, str]:
        options = ", ".join(t.value for t in available_types)
        system = (
            "You tune a self-organizing agent ecosystem's parameters. Given the "
            "available experiment types and the ecosystem's current state, rank the "
            "experiments from most to least promising to try next, choose whether to "
            "'increase' or 'decrease' each, and explain briefly. You choose ONLY the "
            "order and the direction — the (bounded) magnitude and a compassion guard "
            "are enforced downstream, so never reason about exact values or safety. "
            'Return ONLY JSON: {"ranking":[type,...],'
            '"directions":{type:"increase"|"decrease"},"rationale":"..."}'
        )
        state = "\n".join(f"- {k}: {v}" for k, v in sorted(context.items()))
        prompt = (
            f"AVAILABLE EXPERIMENTS: {options}\n\n"
            f"ECOSYSTEM STATE:\n{state}\n\nReturn only the JSON object."
        )
        return system, prompt

    @staticmethod
    def _parse(text: str, available_types: list[ExperimentType]) -> ProposalGuidance:
        data = _extract_json(text)
        if not isinstance(data, dict):
            return ProposalGuidance()
        valid = {t.value: t for t in available_types}

        ordered: list[ExperimentType] = []
        raw = data.get("ranking")
        if isinstance(raw, list):
            for item in raw:
                etype = valid.get(str(item).strip().lower())
                if etype is not None and etype not in ordered:
                    ordered.append(etype)

        directions: dict[ExperimentType, str] = {}
        raw_dirs = data.get("directions")
        if isinstance(raw_dirs, dict):
            for key, value in raw_dirs.items():
                etype = valid.get(str(key).strip().lower())
                direction = str(value).strip().lower()
                if etype is not None and direction in VALID_DIRECTIONS:
                    directions[etype] = direction

        rationale = sanitize_text(str(data.get("rationale", ""))).strip()
        return ProposalGuidance(
            ordered_types=ordered, directions=directions, rationale=rationale
        )


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model response (handles ```fences```)."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, IndexError):
        return {}
