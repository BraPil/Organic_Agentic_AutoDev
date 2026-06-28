"""
src/autoresearch — autonomous self-improvement loop.

Inspired by karpathy/autoresearch: the ecosystem runs fixed-budget experiments
on its own behavioural parameters, keeps improvements, and reverts regressions.

Public API:
  AutoResearchEngine   — the propose → test → commit/rollback loop
  EcosystemEvaluator   — single-scalar ecosystem fitness
  Proposer / Checkpointer — guarded proposal generation + non-destructive revert
  build_engine / attach_to_body — wiring helpers
  Experiment*V0 / ImprovementCycleV0 — typed records (shell)
"""

from __future__ import annotations

from organic_agentic_autodev.autoresearch.contracts import (
    ExperimentProposalV0,
    ExperimentResultV0,
    ExperimentType,
    ImprovementCycleV0,
)
from organic_agentic_autodev.autoresearch.evaluator import EcosystemEvaluator
from organic_agentic_autodev.autoresearch.integration import attach_to_body, build_engine
from organic_agentic_autodev.autoresearch.proposer import Checkpointer, Proposer
from organic_agentic_autodev.autoresearch.runner import AutoResearchEngine

__all__ = [
    "AutoResearchEngine",
    "EcosystemEvaluator",
    "Proposer",
    "Checkpointer",
    "build_engine",
    "attach_to_body",
    "ExperimentType",
    "ExperimentProposalV0",
    "ExperimentResultV0",
    "ImprovementCycleV0",
]
