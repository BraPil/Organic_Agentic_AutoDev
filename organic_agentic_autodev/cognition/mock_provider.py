"""
src/cognition/mock_provider.py

Deterministic, offline cognition provider.

The MockProvider makes NO network calls. It produces a plausible, validated
CognitionResponseV0 derived deterministically from the request, so that:

  - The full test suite runs offline and reproducibly (no API key required).
  - The ecosystem can be exercised end-to-end with "cognition wired in" without
    spending tokens.
  - CI stays green regardless of whether ANTHROPIC_API_KEY is set.

Determinism: the response is seeded from a hash of the request's salient
fields, so the same request always yields the same response — essential for
reproducible tests.
"""

from __future__ import annotations

import hashlib
import random

from organic_agentic_autodev.cognition.contracts import (
    CognitionRequestV0,
    CognitionResponseV0,
    CognitiveAction,
)
from organic_agentic_autodev.cognition.provider import AbstractLLMProvider
from organic_agentic_autodev.utils.helpers import sanitize_text


class MockProvider(AbstractLLMProvider):
    """A deterministic, dependency-free stand-in for a real LLM provider."""

    name = "mock"

    def __init__(self, defer_probability: float = 0.15) -> None:
        # Probability that the mock "decides" it has nothing to add.
        self._defer_probability = defer_probability

    @property
    def is_live(self) -> bool:
        return False

    def _seed_for(self, request: CognitionRequestV0) -> int:
        key = f"{request.role}|{request.task}|{request.tick}|{request.context[:64]}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def complete(self, request: CognitionRequestV0) -> CognitionResponseV0:
        rng = random.Random(self._seed_for(request))

        if rng.random() < self._defer_probability:
            return self.defer_response("mock: nothing to add this step")

        # Choose an action weighted toward contribution.
        action = rng.choices(
            [
                CognitiveAction.CONTRIBUTE_KNOWLEDGE,
                CognitiveAction.SYNTHESISE,
                CognitiveAction.CRITIQUE,
            ],
            weights=[0.6, 0.25, 0.15],
        )[0]

        confidence = round(rng.uniform(0.45, 0.9), 3)
        tags = list(request.available_tags[:2]) + [request.role]
        content = sanitize_text(
            f"[mock:{request.role}] {action.value} at tick {request.tick}: "
            f"reasoned over {len(request.context)} chars of context "
            f"toward '{request.task[:60]}'."
        )
        return CognitionResponseV0(
            action=action,
            content=content[:600],
            confidence=confidence,
            reasoning=f"mock deterministic decision (seed-derived, conf={confidence})",
            topic_tags=tags,
        )
