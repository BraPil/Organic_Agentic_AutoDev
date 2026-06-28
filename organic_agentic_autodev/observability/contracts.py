"""
src/observability/contracts.py

SLA / SLO / SLI typed contracts for the organic agentic ecosystem.

Service Level Agreements (SLAs), Objectives (SLOs), and Indicators (SLIs)
are the observability backbone of a production-grade agentic system.

Definitions:
  SLI (Indicator) — a quantitative measurement of a specific system property
                    (e.g. "current mean knowledge confidence = 0.82")
  SLO (Objective) — a target value for an SLI that the system should meet
                    (e.g. "mean knowledge confidence MUST be >= 0.75")
  SLA (Agreement) — a contractual commitment binding multiple SLOs, with
                    an overall compliance target (e.g. "99% of SLOs met")

This module defines the versioned contracts only (shell).
The Tracker implementation (flesh) lives in tracker.py.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SLIKind(str, Enum):
    """What is being measured."""
    KNOWLEDGE_CONFIDENCE_MEAN = "knowledge_confidence_mean"
    KNOWLEDGE_CONFIDENCE_P95  = "knowledge_confidence_p95"
    NICHE_FILL_RATE           = "niche_fill_rate"
    AGENT_SURVIVAL_RATE       = "agent_survival_rate"
    ADVERSE_EVENT_COVERAGE    = "adverse_event_coverage"   # % agents monitored
    GUIDELINE_ADHERENCE_RATE  = "guideline_adherence_rate"
    CASE_SYNTHESIS_LATENCY    = "case_synthesis_latency"   # ticks
    CONSENSUS_RATE            = "consensus_rate"           # % records reviewed ≥2
    KNOWLEDGE_GROWTH_RATE     = "knowledge_growth_rate"    # records per 10 ticks
    ORGAN_VIABILITY_RATE      = "organ_viability_rate"     # % organs viable
    ENERGY_HEADROOM           = "energy_headroom"          # % energy pool remaining


class SLOStatus(str, Enum):
    """Evaluation outcome for one SLO at a measurement point."""
    MEETING           = "meeting"           # Within target
    AT_RISK           = "at_risk"           # Approaching boundary
    BREACHED          = "breached"          # Objective not met
    INSUFFICIENT_DATA = "insufficient_data" # Not enough measurements yet


class SLIWindowKind(str, Enum):
    """Measurement window for an SLI."""
    CURRENT          = "current"           # Instantaneous snapshot
    ROLLING_10_TICKS = "rolling_10_ticks"
    ROLLING_50_TICKS = "rolling_50_ticks"
    ALL_TIME         = "all_time"


class SLOComparison(str, Enum):
    """How to compare the measured SLI value against the target."""
    GTE = "gte"   # measured >= target  (e.g., confidence must be AT LEAST 0.75)
    LTE = "lte"   # measured <= target  (e.g., latency must be AT MOST 10 ticks)
    EQ  = "eq"    # measured == target  (rare; use GTE/LTE in practice)


# ---------------------------------------------------------------------------
# SLI Measurement
# ---------------------------------------------------------------------------

class SLIMeasurementV0(BaseModel):
    """
    A single timestamped measurement of one Service Level Indicator.

    Every tick the SLITracker computes fresh SLIMeasurements and stores the
    most recent in its ledger for SLO evaluation.
    """
    measurement_id: str
    sli_kind: SLIKind
    value: float
    unit: str                      # e.g., "%", "confidence", "ticks", "records/10t"
    tick: int
    window: SLIWindowKind
    sample_size: int = 0           # number of data points contributing to measurement
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"


# ---------------------------------------------------------------------------
# SLO Definition
# ---------------------------------------------------------------------------

class SLODefinitionV0(BaseModel):
    """
    A Service Level Objective — an observable target the ecosystem must meet.

    Fields
    ------
    slo_id:
        Unique identifier.
    name:
        Human-readable short name (e.g., "knowledge_confidence_floor").
    description:
        Full description of what this objective protects and why it matters.
    sli_kind:
        Which SLI this objective is evaluated against.
    target_value:
        The required value (e.g., 0.75 for minimum mean confidence).
    comparison:
        How to compare: GTE ("≥ target"), LTE ("≤ target"), EQ.
    at_risk_threshold:
        The value at which the SLO transitions to AT_RISK status
        (should be more conservative than ``target_value``).
    window:
        Measurement window to evaluate over.
    priority:
        P1 (critical/patient-safety), P2 (high), P3 (medium).
    min_sample_size:
        Minimum data points needed to evaluate — below this, status is
        INSUFFICIENT_DATA.
    """
    slo_id: str
    name: str
    description: str
    sli_kind: SLIKind
    target_value: float
    comparison: SLOComparison
    at_risk_threshold: float
    window: SLIWindowKind = SLIWindowKind.ROLLING_50_TICKS
    priority: str = "P2"           # "P1", "P2", "P3"
    min_sample_size: int = 1
    schema_version: str = "v0"

    def evaluate(self, measurement: SLIMeasurementV0) -> SLOStatus:
        """Classify the measurement against this SLO's target and thresholds."""
        if measurement.sample_size < self.min_sample_size:
            return SLOStatus.INSUFFICIENT_DATA

        v = measurement.value

        if self.comparison == SLOComparison.GTE:
            if v >= self.target_value:
                return SLOStatus.MEETING
            elif v >= self.at_risk_threshold:
                return SLOStatus.AT_RISK
            else:
                return SLOStatus.BREACHED

        elif self.comparison == SLOComparison.LTE:
            if v <= self.target_value:
                return SLOStatus.MEETING
            elif v <= self.at_risk_threshold:
                return SLOStatus.AT_RISK
            else:
                return SLOStatus.BREACHED

        else:  # EQ
            tolerance = 0.02
            if abs(v - self.target_value) <= tolerance:
                return SLOStatus.MEETING
            elif abs(v - self.target_value) <= self.at_risk_threshold:
                return SLOStatus.AT_RISK
            else:
                return SLOStatus.BREACHED


# ---------------------------------------------------------------------------
# SLO Evaluation (result of evaluating one SLO)
# ---------------------------------------------------------------------------

class SLOEvaluationV0(BaseModel):
    """
    Result of evaluating a single SLO at a given tick.

    Stored in the SLITracker's evaluation ledger.  When breached, the
    tracker emits a DANGER signal to the ecosystem via the Mouseion event bus.
    """
    evaluation_id: str
    slo_id: str
    slo_name: str
    slo_priority: str
    sli_measurement: SLIMeasurementV0
    status: SLOStatus
    delta: float               # (value - target) — positive = meeting, negative = breached
    tick: int
    message: str = ""          # human-readable summary
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"


# ---------------------------------------------------------------------------
# SLA Contract
# ---------------------------------------------------------------------------

class SLAContractV0(BaseModel):
    """
    A Service Level Agreement binding a set of SLOs for one ecosystem.

    The SLA defines:
      - Which SLOs must be met (the set of SLODefinitionV0)
      - The overall compliance target (% of SLOs meeting at any tick)
      - The review cadence (how often the ecosystem evaluates compliance)
    """
    sla_id: str
    name: str
    description: str
    slos: list[SLODefinitionV0] = Field(default_factory=list)
    compliance_target: float = Field(default=0.99, ge=0.0, le=1.0)
    review_period_ticks: int = 50
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"

    def p1_slos(self) -> list[SLODefinitionV0]:
        """Return only the critical (P1) SLOs."""
        return [s for s in self.slos if s.priority == "P1"]

    def p2_slos(self) -> list[SLODefinitionV0]:
        return [s for s in self.slos if s.priority == "P2"]

    def slo_by_id(self, slo_id: str) -> SLODefinitionV0 | None:
        return next((s for s in self.slos if s.slo_id == slo_id), None)
