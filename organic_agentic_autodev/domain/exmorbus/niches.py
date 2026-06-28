"""
src/domain/exmorbus/niches.py

Oncology-specific Niche factory for the ExMorbus ecosystem.

Creates 12 medical niches that seed selection pressure in the ecosystem,
driving StemCell differentiation toward oncological specialist roles.

Niche urgency reflects real clinical priority:
  - High urgency (0.75-0.90): GUARDIAN (safety), PATHOLOGIST (backlog)
  - Medium urgency (0.55-0.74): ONCOLOGIST, GENETICIST, RADIOLOGIST, CLINICAL_TRIALIST
  - Lower urgency (0.40-0.54): PATIENT_ADVOCATE, EPIDEMIOLOGIST, PHARMACOLOGIST
"""

from __future__ import annotations

from organic_agentic_autodev.core.niche import Niche
from organic_agentic_autodev.mouseion.contracts import AgentRole, ResourceKind
from organic_agentic_autodev.utils.helpers import new_id

# ---------------------------------------------------------------------------
# Medical niche definitions
# ---------------------------------------------------------------------------

_MEDICAL_NICHE_SPECS: list[dict] = [
    # --- Critical / high-urgency niches ---
    {
        "role": AgentRole.GUARDIAN,
        "description": (
            "Monitor adverse event signals across patient population — "
            "detect emerging Grade 3/4 toxicity clusters and flag immediately"
        ),
        "urgency": 0.88,
        "urgency_growth_rate": 0.05,   # grows fastest — safety is most urgent
        "reward": {
            ResourceKind.ENERGY: 6.0,
            ResourceKind.TRUST: 9.0,
            ResourceKind.KNOWLEDGE: 3.0,
        },
    },
    {
        "role": AgentRole.PATHOLOGIST,
        "description": (
            "Analyse pending pathology specimens — 12 cases awaiting "
            "histological review and IHC panel interpretation"
        ),
        "urgency": 0.82,
        "urgency_growth_rate": 0.04,
        "reward": {
            ResourceKind.ENERGY: 7.0,
            ResourceKind.KNOWLEDGE: 6.0,
            ResourceKind.TRUST: 2.0,
        },
    },
    # --- High-urgency niches ---
    {
        "role": AgentRole.ONCOLOGIST,
        "description": (
            "Synthesise multi-modal case data (genomic + pathology + imaging) "
            "into treatment recommendation for new patient cohort"
        ),
        "urgency": 0.75,
        "urgency_growth_rate": 0.03,
        "reward": {
            ResourceKind.ENERGY: 8.0,
            ResourceKind.KNOWLEDGE: 5.0,
            ResourceKind.TRUST: 3.0,
        },
    },
    {
        "role": AgentRole.GENETICIST,
        "description": (
            "Interpret NGS panel results for 8 patients — "
            "identify actionable mutations and tier pathogenic variants"
        ),
        "urgency": 0.72,
        "urgency_growth_rate": 0.032,
        "reward": {
            ResourceKind.ENERGY: 7.0,
            ResourceKind.KNOWLEDGE: 8.0,
            ResourceKind.TRUST: 1.0,
        },
    },
    {
        "role": AgentRole.RADIOLOGIST,
        "description": (
            "Perform RECIST 1.1 imaging response assessment at 8-week checkpoint "
            "for 15 patients on active treatment protocols"
        ),
        "urgency": 0.76,
        "urgency_growth_rate": 0.035,
        "reward": {
            ResourceKind.ENERGY: 6.0,
            ResourceKind.KNOWLEDGE: 5.0,
            ResourceKind.TRUST: 2.0,
        },
    },
    {
        "role": AgentRole.CLINICAL_TRIALIST,
        "description": (
            "Screen patient roster for eligibility in 3 active clinical trials "
            "(EGFR+, MSI-H, and HER2+ cohorts)"
        ),
        "urgency": 0.62,
        "urgency_growth_rate": 0.022,
        "reward": {
            ResourceKind.ENERGY: 6.0,
            ResourceKind.KNOWLEDGE: 4.0,
            ResourceKind.TRUST: 4.0,
        },
    },
    {
        "role": AgentRole.PHARMACOLOGIST,
        "description": (
            "Review drug interaction database for checkpoint inhibitor + "
            "concomitant medication combinations across active patient cohort"
        ),
        "urgency": 0.66,
        "urgency_growth_rate": 0.028,
        "reward": {
            ResourceKind.ENERGY: 5.0,
            ResourceKind.TRUST: 6.0,
            ResourceKind.KNOWLEDGE: 2.0,
        },
    },
    # --- Medium-urgency niches ---
    {
        "role": AgentRole.PATIENT_ADVOCATE,
        "description": (
            "Conduct quality-of-life assessments and identify patients "
            "requiring early palliative care integration"
        ),
        "urgency": 0.52,
        "urgency_growth_rate": 0.016,
        "reward": {
            ResourceKind.ENERGY: 4.0,
            ResourceKind.TRUST: 6.0,
            ResourceKind.KNOWLEDGE: 2.0,
        },
    },
    {
        "role": AgentRole.EPIDEMIOLOGIST,
        "description": (
            "Analyse cohort-level treatment response patterns — "
            "identify subgroup differences in immunotherapy outcomes"
        ),
        "urgency": 0.55,
        "urgency_growth_rate": 0.018,
        "reward": {
            ResourceKind.ENERGY: 5.0,
            ResourceKind.KNOWLEDGE: 7.0,
            ResourceKind.TRUST: 1.0,
        },
    },
    # --- Supporting generic roles (enable mixed ecosystems) ---
    {
        "role": AgentRole.SYNTHESIZER,
        "description": (
            "Integrate tumor board outputs from multiple specialties into "
            "unified patient management summaries"
        ),
        "urgency": 0.68,
        "urgency_growth_rate": 0.025,
        "reward": {
            ResourceKind.ENERGY: 6.0,
            ResourceKind.KNOWLEDGE: 5.0,
            ResourceKind.TRUST: 2.0,
        },
    },
    {
        "role": AgentRole.RESEARCHER,
        "description": (
            "Survey recent oncology literature for novel biomarker-treatment "
            "associations to update the Mouseion knowledge base"
        ),
        "urgency": 0.50,
        "urgency_growth_rate": 0.012,
        "reward": {
            ResourceKind.ENERGY: 5.0,
            ResourceKind.KNOWLEDGE: 10.0,
            ResourceKind.TRUST: 0.0,
        },
    },
    {
        "role": AgentRole.CURATOR,
        "description": (
            "Audit Mouseion knowledge records for guideline currency — "
            "flag protocols superseded by 2024 NCCN/ASCO updates"
        ),
        "urgency": 0.45,
        "urgency_growth_rate": 0.010,
        "reward": {
            ResourceKind.ENERGY: 4.0,
            ResourceKind.KNOWLEDGE: 3.0,
            ResourceKind.TRUST: 4.0,
        },
    },
]


def create_medical_niches() -> list[Niche]:
    """
    Return the full set of oncology-specific Niche objects.

    Each niche encodes:
      - The specialist role needed (drives StemCell differentiation)
      - A clinical description (what the ecosystem currently needs)
      - Initial urgency (how pressing the need is)
      - Urgency growth rate (how quickly it becomes more urgent if unfilled)
      - Resource reward (what the filling agent receives)

    Returns
    -------
    list[Niche]
        12 medical niches ordered from highest to lowest urgency.
    """
    niches: list[Niche] = []
    for spec in _MEDICAL_NICHE_SPECS:
        niches.append(Niche(
            niche_id=new_id("med_niche_"),
            role=spec["role"],
            description=spec["description"],
            urgency=spec["urgency"],
            urgency_growth_rate=spec["urgency_growth_rate"],
            base_reward=spec["reward"],
        ))
    return niches
