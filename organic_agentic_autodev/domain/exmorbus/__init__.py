"""
src/domain/exmorbus/__init__.py

ExMorbus domain module — medical/oncological focus.

ExMorbus (Latin: "from disease") provides the oncological seed knowledge,
specialist niches, and genome profiles that guide the first generation of
medical StemCells toward differentiation into a functioning oncology
research ecosystem.

Key exports:
  - MedicalKnowledgeType, ClinicalEvidenceLevel, OncologyDomain  — domain contracts
  - MedicalKnowledgeRecordV0  — extended knowledge record for medical content
  - seed_mouseion()           — pre-populates Mouseion with oncological knowledge
  - create_medical_niches()   — returns 12 oncology-specific Niche objects
  - create_medical_genome()   — returns Genome biased toward a medical role
"""

from organic_agentic_autodev.domain.exmorbus.contracts import (
    AdverseEventSeverity,
    ClinicalEvidenceLevel,
    MedicalKnowledgeRecordV0,
    MedicalKnowledgeType,
    OncologyDomain,
)
from organic_agentic_autodev.domain.exmorbus.genome_profiles import create_medical_genome, MEDICAL_ROLE_BIAS
from organic_agentic_autodev.domain.exmorbus.niches import create_medical_niches
from organic_agentic_autodev.domain.exmorbus.seeder import seed_mouseion

__all__ = [
    "AdverseEventSeverity",
    "ClinicalEvidenceLevel",
    "MedicalKnowledgeRecordV0",
    "MedicalKnowledgeType",
    "OncologyDomain",
    "create_medical_genome",
    "MEDICAL_ROLE_BIAS",
    "create_medical_niches",
    "seed_mouseion",
]
