"""
src/cognition/provider.py

The AbstractLLMProvider shell contract.

Every cognition backend — Anthropic (default), OpenAI, or the deterministic
MockProvider — implements this interface. This is the seam that makes LLM
cognition hot-swappable flesh: the rest of the system depends only on this
abstract class, never on a concrete SDK.

Providers are responsible for:
  - Translating a CognitionRequestV0 into a provider-specific call
  - Forcing structured output so the result validates as CognitionResponseV0
  - Defensive sanitisation of any text that will re-enter the Mouseion
  - Never raising on a transient failure — return a safe DEFER response instead,
    so the simulation loop never dies because an API call timed out.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from organic_agentic_autodev.cognition.contracts import (
    CognitionRequestV0,
    CognitionResponseV0,
    CognitiveAction,
)
from organic_agentic_autodev.utils.helpers import get_logger

logger = get_logger("cognition.provider")


class AbstractLLMProvider(ABC):
    """Base class for all cognition providers."""

    #: Human-readable provider name (e.g. "anthropic", "openai", "mock").
    name: str = "abstract"

    @abstractmethod
    def complete(self, request: CognitionRequestV0) -> CognitionResponseV0:
        """
        Perform one cognition call and return a validated response.

        Implementations MUST NOT raise on transient errors — catch and return
        ``AbstractLLMProvider.defer_response(...)`` so the ecosystem keeps
        ticking even when the backend is unavailable.
        """
        raise NotImplementedError

    @property
    def is_live(self) -> bool:
        """True if this provider makes real network calls (vs. mock/offline)."""
        return False

    @staticmethod
    def defer_response(reason: str = "no contribution") -> CognitionResponseV0:
        """A safe, no-op response used as a fallback when cognition fails."""
        return CognitionResponseV0(
            action=CognitiveAction.DEFER,
            content="",
            confidence=0.0,
            reasoning=reason[:300],
            topic_tags=[],
        )
