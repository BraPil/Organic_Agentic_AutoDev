"""
src/domain/exmorbus/contracts.py

Medical / oncological domain contracts for ExMorbus.

These are domain-specific extensions layered on top of the core Mouseion
contracts.  They are shell contracts (rarely change) following the MoltBook
pattern: stable, versioned, Pydantic-validated.

Key types:
  MedicalKnowledgeType  — category of oncological record
  ClinicalEvidenceLevel — hierarchy of evidence strength (RCT > expert_opinion)
  OncologyDomain        — cancer type / organ system
  AdverseEventSeverity  — CTCAE toxicity grades 1-5
  MedicalKnowledgeRecordV0 — extends KnowledgeRecordV0 with domain metadata
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MedicalKnowledgeType(str, Enum):
    """Category of oncological knowledge record."""
    CLINICAL_TRIAL = "clinical_trial"
    PATHOLOGY_REPORT = "pathology_report"
    GENOMIC_PROFILE = "genomic_profile"
    TREATMENT_PROTOCOL = "treatment_protocol"
    ADVERSE_EVENT = "adverse_event"
    IMAGING_FINDING = "imaging_finding"
    BIOMARKER_ASSESSMENT = "biomarker_assessment"
    GUIDELINE = "guideline"
    SYNTHESIS = "synthesis"
    PATIENT_OUTCOME = "patient_outcome"
    EPIDEMIOLOGY = "epidemiology"


class ClinicalEvidenceLevel(str, Enum):
    """
    Hierarchy of clinical evidence strength (descending).

    Used to weight the confidence score of a knowledge record:
      RCT and SYSTEMATIC_REVIEW → high confidence
      EXPERT_OPINION / PRECLINICAL → lower confidence
    """
    RCT = "rct"                            # Randomised controlled trial (highest)
    SYSTEMATIC_REVIEW = "systematic_review"
    COHORT_STUDY = "cohort_study"
    CASE_CONTROL = "case_control"
    CASE_SERIES = "case_series"
    EXPERT_OPINION = "expert_opinion"
    PRECLINICAL = "preclinical"             # In-vitro / animal data (lowest)

    @property
    def confidence_weight(self) -> float:
        """Map evidence level to a confidence multiplier [0.55, 1.0]."""
        _MAP = {
            "rct": 1.0,
            "systematic_review": 0.95,
            "cohort_study": 0.82,
            "case_control": 0.72,
            "case_series": 0.62,
            "expert_opinion": 0.57,
            "preclinical": 0.55,
        }
        return _MAP.get(self.value, 0.60)


class OncologyDomain(str, Enum):
    """Oncological specialty / organ system."""
    BREAST = "breast"
    LUNG = "lung"
    COLORECTAL = "colorectal"
    HEMATOLOGIC = "hematologic"
    OVARIAN = "ovarian"
    PROSTATE = "prostate"
    MELANOMA = "melanoma"
    PANCREATIC = "pancreatic"
    GLIOBLASTOMA = "glioblastoma"
    GENERAL = "general"               # Pan-tumour / cross-domain


class AdverseEventSeverity(str, Enum):
    """CTCAE toxicity grades."""
    GRADE_1 = "grade_1"   # Mild — asymptomatic or mild symptoms
    GRADE_2 = "grade_2"   # Moderate — minimal intervention indicated
    GRADE_3 = "grade_3"   # Severe — hospitalisation warranted
    GRADE_4 = "grade_4"   # Life-threatening — urgent intervention required
    GRADE_5 = "grade_5"   # Fatal


# ---------------------------------------------------------------------------
# Domain contracts (v0)
# ---------------------------------------------------------------------------

class MedicalKnowledgeRecordV0(BaseModel):
    """
    Extended metadata for oncological knowledge records.

    Pairs with KnowledgeRecordV0 via ``base_record_id``:
        mouseion_record = mouseion.store_knowledge(...)
        medical_meta    = MedicalKnowledgeRecordV0(
                              base_record_id=mouseion_record.record_id, ...)

    The medical record enriches the base record with domain semantics
    (evidence level, oncology domain, clinical significance) without
    polluting the core Mouseion contracts.
    """
    base_record_id: str
    knowledge_type: MedicalKnowledgeType
    evidence_level: ClinicalEvidenceLevel = ClinicalEvidenceLevel.EXPERT_OPINION
    oncology_domain: OncologyDomain = OncologyDomain.GENERAL
    patient_population: str = ""        # e.g. "HER2+ breast cancer, stage III"
    clinical_significance: float = Field(default=0.5, ge=0.0, le=1.0)
    guideline_aligned: bool | None = None
    source_references: list[str] = Field(default_factory=list)
    review_status: str = "pending"      # pending / reviewed / validated / superseded
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"

    @property
    def effective_confidence(self) -> float:
        """Blend clinical_significance with evidence_level weight."""
        return min(1.0, self.clinical_significance * self.evidence_level.confidence_weight)


class AdverseEventRecordV0(BaseModel):
    """Structured adverse event record for pharmacovigilance tracking."""
    event_id: str
    base_record_id: str
    severity: AdverseEventSeverity
    agent_id: str                       # reporting agent
    affected_agents: list[str] = Field(default_factory=list)
    description: str
    intervention_recommended: str = ""
    tick_detected: int = 0
    resolved: bool = False
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"


class TreatmentRecommendationV0(BaseModel):
    """A structured treatment recommendation produced by an Oncologist cell."""
    recommendation_id: str
    base_record_id: str
    author_agent_id: str
    oncology_domain: OncologyDomain
    recommended_regimen: str
    evidence_level: ClinicalEvidenceLevel
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    contraindications: list[str] = Field(default_factory=list)
    provenance_record_ids: list[str] = Field(default_factory=list)
    tick_produced: int = 0
    reviewed_by: list[str] = Field(default_factory=list)   # agent IDs
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    schema_version: str = "v0"


class ClinicalTrialMatchV0(BaseModel):
    """A patient-trial match produced by a ClinicalTrialist cell."""
    match_id: str
    base_record_id: str
    trial_name: str
    eligibility_criteria: list[str] = Field(default_factory=list)
    match_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    biomarker_refs: list[str] = Field(default_factory=list)  # genomic record IDs
    tick_produced: int = 0
    schema_version: str = "v0"
