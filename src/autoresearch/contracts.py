"""
src/autoresearch/contracts.py

Shell contracts for the autoresearch self-improvement loop.

Inspired by karpathy/autoresearch: the ecosystem proposes a change to one of
its own parameters, runs a fixed-budget experiment, measures the fitness delta,
and keeps the change only if it improved — otherwise it rolls back. These typed
records make each experiment auditable and storable in the Mouseion.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExperimentType(str, Enum):
    """A tunable knob the ecosystem may experiment on."""
    NICHE_URGENCY_GROWTH = "niche_urgency_growth"   # how fast an unfilled niche heats up
    ENERGY_REGEN = "energy_regen"                   # resource pool regeneration rate
    CARRYING_CAPACITY = "carrying_capacity"         # selector population ceiling
    MUTATION_RATE = "mutation_rate"                 # genome mutation rate
    SELECTION_STRENGTH = "selection_strength"       # how harshly low fitness is penalised


class ExperimentProposalV0(BaseModel):
    """A proposed parameter change to test."""
    experiment_id: str
    experiment_type: ExperimentType
    target: str                  # what is being changed (e.g. niche_id or "global")
    old_value: float
    new_value: float
    rationale: str = ""
    schema_version: str = "v0"


class ExperimentResultV0(BaseModel):
    """The measured outcome of running one experiment."""
    experiment_id: str
    baseline_score: float
    result_score: float
    delta: float
    committed: bool              # True = improvement kept, False = rolled back
    ticks_run: int
    rejected_reason: str = ""    # populated when a proposal was blocked pre-run
    schema_version: str = "v0"


class ImprovementCycleV0(BaseModel):
    """One full propose → run → evaluate → commit/rollback cycle."""
    cycle_id: str
    tick: int
    proposal: ExperimentProposalV0 | None = None
    result: ExperimentResultV0 | None = None
    notes: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "v0"
