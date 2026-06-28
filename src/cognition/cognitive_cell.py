"""
src/cognition/cognitive_cell.py

CognitiveCell — a Cell whose role action is driven by an LLM.

This is the bridge between the pure-Python simulation and real AI cognition.
A CognitiveCell behaves exactly like a Cell, except that during its role action
it may invoke an LLM provider to *decide* what knowledge to contribute, instead
of emitting a stochastic template.

Key properties (MoltBook flesh-on-Layer-2):
  - Subclasses Cell — inherits clustering, organ membership, signalling, energy.
  - The genome → system-prompt bias is built once and cached on the instance
    (stable cache prefix for prompt caching).
  - Lazy invocation: at most one LLM call per tick, gated by a probability so a
    large colony doesn't make a call for every agent every tick.
  - Graceful degradation: if the provider DEFERs or returns nothing usable, the
    cell falls back to the normal stochastic Cell behaviour. The ecosystem never
    stalls on cognition.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.cognition.contracts import CognitionRequestV0, CognitiveAction
from src.cognition.genome_prompt import build_system_prompt
from src.cognition.mock_provider import MockProvider
from src.cognition.provider import AbstractLLMProvider
from src.core.genome import Genome
from src.mouseion.contracts import AgentRole
from src.organisms.cell import Cell
from src.utils.helpers import clamp, get_logger, sanitize_text

if TYPE_CHECKING:
    from src.core.environment import Environment

logger = get_logger("cognition.cell")


class CognitiveCell(Cell):
    """A differentiated Cell that reasons via an LLM provider."""

    def __init__(
        self,
        role: AgentRole,
        provider: AbstractLLMProvider | None = None,
        cognition_probability: float = 0.5,
        genome: Genome | None = None,
        initial_energy: float = 10.0,
        parent_id: str | None = None,
        rng: random.Random | None = None,
    ) -> None:
        super().__init__(role=role, genome=genome, initial_energy=initial_energy,
                         parent_id=parent_id, rng=rng)
        # Default to the offline MockProvider so a CognitiveCell is always safe
        # to instantiate, even with no API key configured.
        self._provider: AbstractLLMProvider = provider or MockProvider()
        self._cognition_probability = cognition_probability
        # Built once — stable cache prefix for prompt caching.
        self._system_prompt = build_system_prompt(self.genome, self.role)
        self._cognition_count = 0

    # ------------------------------------------------------------------
    # Cognition
    # ------------------------------------------------------------------

    def _perform_role_action(self, env: "Environment") -> None:
        """Reason via the LLM, then fall back to stochastic behaviour."""
        did_cognition = False
        if self.rng.random() < self._cognition_probability:
            did_cognition = self._cognitive_action(env)

        # Always run the inherited stochastic behaviour too, unless cognition
        # already produced a contribution this tick (avoid double-spending).
        if not did_cognition:
            super()._perform_role_action(env)
        else:
            # Still grow specialisation, mirroring the base class.
            self.specialisation_score = clamp(
                self.specialisation_score + 0.01 * self.genome.persistence
            )

    def _cognitive_action(self, env: "Environment") -> bool:
        """
        Run one cognition call. Returns True if a knowledge record was produced.
        """
        request = self._build_request(env)
        response = self._provider.complete(request)
        self._cognition_count += 1

        if response.action == CognitiveAction.DEFER or not response.content.strip():
            return False

        record = env.mouseion.store_knowledge(
            author_id=self.agent_id,
            content=sanitize_text(response.content),
            topic_tags=self._merge_tags(response.topic_tags),
            confidence=clamp(response.confidence),
        )
        logger.debug(
            "CognitiveCell %s (%s) contributed %s via %s (conf=%.2f)",
            self.agent_id, self.role.value, record.record_id,
            self._provider.name, response.confidence,
        )
        return True

    def _build_request(self, env: "Environment") -> CognitionRequestV0:
        """Assemble a sanitised cognition request from local Mouseion context."""
        # Draw a small, role-relevant slice of context — local information only.
        relevant_tags = self._context_tags()
        snippets: list[str] = []
        for tag in relevant_tags:
            for rec in env.mouseion.query_knowledge(tag)[:2]:
                snippets.append(f"[{tag}] {rec.content}")
        context = sanitize_text("\n".join(snippets)[:4000])

        return CognitionRequestV0(
            role=self.role.value,
            genome_bias=self._system_prompt,
            task=self._role_task(),
            context=context,
            available_tags=relevant_tags,
            tick=env.tick_count,
        )

    # ------------------------------------------------------------------
    # Role-specific context selection
    # ------------------------------------------------------------------

    def _context_tags(self) -> list[str]:
        """Tags this role draws on when reasoning (local, role-relevant)."""
        base = [self.role.value]
        role_context: dict[AgentRole, list[str]] = {
            AgentRole.ONCOLOGIST: ["genomics", "pathology", "treatment_protocol", "oncology"],
            AgentRole.GENETICIST: ["genomics", "oncology"],
            AgentRole.PATHOLOGIST: ["pathology", "histology", "oncology"],
            AgentRole.RADIOLOGIST: ["imaging_finding", "recist", "oncology"],
            AgentRole.PHARMACOLOGIST: ["drug_safety", "toxicity", "oncology"],
            AgentRole.CLINICAL_TRIALIST: ["clinical_trial", "genomics", "oncology"],
            AgentRole.EPIDEMIOLOGIST: ["oncology", "clinical_trial", "treatment_protocol"],
            AgentRole.PATIENT_ADVOCATE: ["patient_outcomes", "palliative_care", "oncology"],
            AgentRole.RESEARCHER: ["research", "innovation"],
            AgentRole.SYNTHESIZER: ["research", "code", "innovation"],
            AgentRole.CRITIC: ["research", "code"],
        }
        return base + role_context.get(self.role, ["research"])

    def _role_task(self) -> str:
        """The standing task this role pursues each cognition step."""
        return (
            f"As a {self.role.value.replace('_', ' ')}, review the available context "
            "and contribute one focused, well-grounded knowledge record that advances "
            "the ecosystem's current goal, or DEFER if you have nothing of value to add."
        )

    def _merge_tags(self, response_tags: list[str]) -> list[str]:
        """Combine model-suggested tags with role-canonical tags, deduplicated."""
        tags = list(dict.fromkeys([self.role.value, *response_tags]))
        return [sanitize_text(t)[:40] for t in tags][:8]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def cognition_count(self) -> int:
        return self._cognition_count

    def snapshot(self) -> dict:
        base = super().snapshot()
        base.update({
            "provider": self._provider.name,
            "cognition_count": self._cognition_count,
            "is_live_cognition": self._provider.is_live,
        })
        return base
