"""
src/mouseion/contracts.py

Mouseion Core v0 — stable typed contracts for cross-agent communication.
Inspired by BraPil/Agentic-AI-Architect's mouseion.py shell contracts.

Shell contracts change slowly (major versions).
Flesh implementations (LLM providers, vector stores) change rapidly.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class EventKind(str, Enum):
    RESOURCE_DISCOVERED = "resource_discovered"
    NICHE_OPENED = "niche_opened"
    NICHE_FILLED = "niche_filled"
    DIFFERENTIATION_STARTED = "differentiation_started"
    DIFFERENTIATION_COMPLETED = "differentiation_completed"
    CELL_CLUSTERED = "cell_clustered"
    ORGAN_FORMED = "organ_formed"
    BODY_ASSEMBLED = "body_assembled"
    SIGNAL_PROPAGATED = "signal_propagated"
    FITNESS_EVALUATED = "fitness_evaluated"
    KNOWLEDGE_STORED = "knowledge_stored"
    TASK_REQUESTED = "task_requested"
    TASK_COMPLETED = "task_completed"
    AGENT_DIED = "agent_died"


class AgentRole(str, Enum):
    # --- Generic roles (original ecosystem) ---
    STEM_CELL = "stem_cell"
    RESEARCHER = "researcher"
    CODER = "coder"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"
    CURATOR = "curator"
    CONNECTOR = "connector"
    INNOVATOR = "innovator"
    GUARDIAN = "guardian"

    # --- Oncology / Medical specialist roles (ExMorbus) ---
    ONCOLOGIST = "oncologist"           # Treatment-decision synthesis; compassion-driven
    PATHOLOGIST = "pathologist"         # Histology & IHC analysis; precision-focused
    CLINICAL_TRIALIST = "clinical_trialist"  # Trial design, eligibility & outcomes
    GENETICIST = "geneticist"           # Genomic variant interpretation & annotation
    PHARMACOLOGIST = "pharmacologist"   # Drug safety, interactions & dosing
    RADIOLOGIST = "radiologist"         # Imaging response (RECIST/iRECIST)
    PATIENT_ADVOCATE = "patient_advocate"   # Quality-of-life & palliative integration
    EPIDEMIOLOGIST = "epidemiologist"   # Population-level cohort pattern analysis


class ResourceKind(str, Enum):
    ENERGY = "energy"
    COMPUTE = "compute"
    DATA = "data"
    ATTENTION = "attention"
    KNOWLEDGE = "knowledge"
    TRUST = "trust"


# ---------------------------------------------------------------------------
# Core shell contracts (v0) — versioned for long-lived stability
# ---------------------------------------------------------------------------

class EventEnvelopeV0(BaseModel):
    """Stable wrapper for all cross-agent events."""
    event_id: str
    kind: EventKind
    source_agent_id: str
    target_agent_id: str | None = None
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "v0"

    model_config = {"frozen": True}


class AgentProfileV0(BaseModel):
    """Reusable agent representation — who the agent is and what it can do."""
    agent_id: str
    role: AgentRole
    capabilities: list[str] = Field(default_factory=list)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    energy: float = Field(default=1.0, ge=0.0)
    generation: int = 0
    parent_id: str | None = None
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskRequestV0(BaseModel):
    """Work request issued by one agent to another (or to the ecosystem)."""
    task_id: str
    requester_id: str
    assignee_id: str | None = None
    description: str
    resource_budget: dict[ResourceKind, float] = Field(default_factory=dict)
    deadline_ms: int | None = None
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    schema_version: str = "v0"


class TaskResultV0(BaseModel):
    """Result delivered after a task completes or fails."""
    task_id: str
    executor_id: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    resources_consumed: dict[ResourceKind, float] = Field(default_factory=dict)
    duration_ms: int = 0
    error: str | None = None
    schema_version: str = "v0"


class EvaluationV0(BaseModel):
    """Standardised evaluation record with per-criterion scoring."""
    evaluation_id: str
    subject_id: str
    evaluator_id: str
    criteria: dict[str, float] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str = ""
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"


class KnowledgeRecordV0(BaseModel):
    """Durable memory with provenance — stored in the Mouseion substrate."""
    record_id: str
    author_id: str
    content: str
    content_hash: str
    topic_tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    provenance_refs: list[str] = Field(default_factory=list)
    review_history: list[EvaluationV0] = Field(default_factory=list)
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    updated_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"


class NicheAdvertisementV0(BaseModel):
    """A functional role the ecosystem needs filled — posted to the Mouseion."""
    niche_id: str
    description: str
    required_capabilities: list[str] = Field(default_factory=list)
    resource_reward: dict[ResourceKind, float] = Field(default_factory=dict)
    urgency: float = Field(default=0.5, ge=0.0, le=1.0)
    posted_by: str
    filled_by: str | None = None
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"
