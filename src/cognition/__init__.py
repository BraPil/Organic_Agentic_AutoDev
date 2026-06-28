"""
src/cognition — LLM-backed agent cognition.

Public API (shell) for wiring real AI reasoning into the organic ecosystem.

The provider factory ``get_provider()`` selects a backend from the environment:

    OAAD_LLM_PROVIDER = anthropic | openai | mock   (default: auto)
        - "auto": Anthropic if ANTHROPIC_API_KEY is set, else OpenAI if
          OPENAI_API_KEY is set, else the offline MockProvider.
    OAAD_LLM_MODEL    = <model id override>

This keeps the system runnable with zero configuration (falls back to the
deterministic, offline MockProvider) while plugging in a real model the moment
an API key is present — the MoltBook promise: swap the flesh, keep the shell.
"""

from __future__ import annotations

import os

from src.cognition.contracts import (
    CognitionRequestV0,
    CognitionResponseV0,
    CognitiveAction,
)
from src.cognition.cognitive_cell import CognitiveCell
from src.cognition.genome_prompt import build_system_prompt, genome_to_bias, role_mission
from src.cognition.mock_provider import MockProvider
from src.cognition.provider import AbstractLLMProvider
from src.utils.helpers import get_logger

logger = get_logger("cognition")

__all__ = [
    "AbstractLLMProvider",
    "MockProvider",
    "CognitiveCell",
    "CognitionRequestV0",
    "CognitionResponseV0",
    "CognitiveAction",
    "build_system_prompt",
    "genome_to_bias",
    "role_mission",
    "get_provider",
]


def get_provider(kind: str | None = None) -> AbstractLLMProvider:
    """
    Return a cognition provider selected by ``kind`` or the environment.

    Parameters
    ----------
    kind:
        "anthropic", "openai", "mock", or "auto"/None. If None, reads
        ``OAAD_LLM_PROVIDER`` (default "auto").

    Falls back to the offline MockProvider whenever a live provider cannot be
    constructed — so this never raises and the ecosystem always has cognition.
    """
    kind = (kind or os.environ.get("OAAD_LLM_PROVIDER", "auto")).lower()

    if kind == "mock":
        return MockProvider()

    if kind in ("anthropic", "auto") and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from src.cognition.anthropic_provider import AnthropicProvider
            logger.info("Cognition provider: anthropic")
            return AnthropicProvider()
        except Exception as exc:  # pragma: no cover - import/runtime guard
            logger.warning("Anthropic provider unavailable (%s); falling back", exc)

    if kind in ("openai", "auto") and os.environ.get("OPENAI_API_KEY"):
        try:
            from src.cognition.openai_provider import OpenAIProvider
            logger.info("Cognition provider: openai")
            return OpenAIProvider()
        except Exception as exc:  # pragma: no cover - import/runtime guard
            logger.warning("OpenAI provider unavailable (%s); falling back", exc)

    if kind in ("anthropic", "openai"):
        # Explicit request for a live provider but no key — surface a clear log
        # and degrade to mock so callers still get a working provider.
        logger.warning("No API key for requested provider '%s'; using MockProvider", kind)

    logger.info("Cognition provider: mock (offline)")
    return MockProvider()
