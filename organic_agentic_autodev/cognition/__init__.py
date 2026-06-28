"""
src/cognition — agent cognition (the flesh that makes cells think).

This package hosts two complementary cognition layers that share the same
shell/flesh philosophy:

1. Per-cell cognition (the LLM-backed agent loop)
   ``get_provider()`` selects a backend from the environment so a differentiated
   ``CognitiveCell`` can reason via an LLM:

       OAAD_LLM_PROVIDER = anthropic | openai | mock   (default: auto)
       OAAD_LLM_MODEL    = <model id override>

   Zero configuration falls back to the deterministic, offline ``MockProvider``.

2. The OAA→AAA cognition bridge (``bridge.py`` / ``run_cycle.py``)
   A Researcher→Critic→Synthesizer ``LearningCycle`` that turns role dynamics
   into real, grounded research and emits ``KnowledgeRecordV0`` artifacts.
   ``CognitionProvider`` is the shell contract; ``AnthropicCognition`` and
   ``DeterministicCognition`` are swappable flesh.

The MoltBook promise throughout: swap the flesh, keep the shell.
"""

from __future__ import annotations

import os

# --- Per-cell LLM cognition ---
from organic_agentic_autodev.cognition.contracts import (
    CognitionRequestV0,
    CognitionResponseV0,
    CognitiveAction,
)
from organic_agentic_autodev.cognition.cognitive_cell import CognitiveCell
from organic_agentic_autodev.cognition.genome_prompt import build_system_prompt, genome_to_bias, role_mission
from organic_agentic_autodev.cognition.mock_provider import MockProvider
from organic_agentic_autodev.cognition.provider import AbstractLLMProvider

# --- OAA→AAA cognition bridge (Researcher/Critic/Synthesizer cycle) ---
from organic_agentic_autodev.cognition.bridge import (
    AnthropicCognition,
    CognitionProvider,
    DeterministicCognition,
    LearningCycle,
    make_cognition,
)
from organic_agentic_autodev.utils.helpers import get_logger

logger = get_logger("cognition")

__all__ = [
    # Per-cell LLM cognition
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
    # OAA→AAA cognition bridge
    "CognitionProvider",
    "AnthropicCognition",
    "DeterministicCognition",
    "LearningCycle",
    "make_cognition",
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
            from organic_agentic_autodev.cognition.anthropic_provider import AnthropicProvider
            logger.info("Cognition provider: anthropic")
            return AnthropicProvider()
        except Exception as exc:  # pragma: no cover - import/runtime guard
            logger.warning("Anthropic provider unavailable (%s); falling back", exc)

    if kind in ("openai", "auto") and os.environ.get("OPENAI_API_KEY"):
        try:
            from organic_agentic_autodev.cognition.openai_provider import OpenAIProvider
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
