"""
src/domain/exmorbus/genome_profiles.py

Genome factory functions for medical / oncological specialist roles.

Each medical role has a distinct trait profile that reflects the skills and
dispositions needed for that specialty:

  ONCOLOGIST       — high compassion + persistence + creativity (patient-centred care)
  PATHOLOGIST      — high persistence + specialisation + low risk_tolerance (precision)
  CLINICAL_TRIALIST — high curiosity + cooperation + risk_tolerance (discovery)
  GENETICIST       — high curiosity + specialisation + persistence (accuracy)
  PHARMACOLOGIST   — high persistence + resilience + low risk_tolerance (safety)
  RADIOLOGIST      — high specialisation + persistence (measurement precision)
  PATIENT_ADVOCATE — high compassion + cooperation + resilience (care)
  EPIDEMIOLOGIST   — high curiosity + creativity + cooperation (pattern finding)
"""

from __future__ import annotations

import random

from organic_agentic_autodev.core.genome import Genome
from organic_agentic_autodev.mouseion.contracts import AgentRole
from organic_agentic_autodev.utils.helpers import clamp


# ---------------------------------------------------------------------------
# Trait means for each medical role  (values are μ for Gaussian sampling)
# ---------------------------------------------------------------------------

MEDICAL_ROLE_BIAS: dict[AgentRole, dict[str, float]] = {
    AgentRole.ONCOLOGIST: {
        "curiosity": 0.65,
        "risk_tolerance": 0.45,
        "cooperation": 0.75,
        "specialisation": 0.70,
        "compassion": 0.88,           # primary driver — patient-centred
        "resilience": 0.65,
        "creativity": 0.70,
        "persistence": 0.80,
        "differentiation_threshold": 0.60,
        "differentiation_min_energy": 0.35,
    },
    AgentRole.PATHOLOGIST: {
        "curiosity": 0.55,
        "risk_tolerance": 0.25,       # low — avoids diagnostic errors
        "cooperation": 0.55,
        "specialisation": 0.85,       # primary driver — deep domain expertise
        "compassion": 0.60,
        "resilience": 0.60,
        "creativity": 0.50,
        "persistence": 0.85,          # primary driver — methodical
        "differentiation_threshold": 0.58,
        "differentiation_min_energy": 0.38,
    },
    AgentRole.CLINICAL_TRIALIST: {
        "curiosity": 0.88,            # primary driver — discovery orientation
        "risk_tolerance": 0.55,       # moderate — tests hypotheses
        "cooperation": 0.72,
        "specialisation": 0.60,
        "compassion": 0.70,
        "resilience": 0.65,
        "creativity": 0.65,
        "persistence": 0.78,
        "differentiation_threshold": 0.62,
        "differentiation_min_energy": 0.33,
    },
    AgentRole.GENETICIST: {
        "curiosity": 0.88,            # primary driver — data explorer
        "risk_tolerance": 0.40,
        "cooperation": 0.58,
        "specialisation": 0.85,       # primary driver — molecular precision
        "compassion": 0.58,
        "resilience": 0.60,
        "creativity": 0.62,
        "persistence": 0.80,
        "differentiation_threshold": 0.58,
        "differentiation_min_energy": 0.35,
    },
    AgentRole.PHARMACOLOGIST: {
        "curiosity": 0.68,
        "risk_tolerance": 0.22,       # very low — safety-first mindset
        "cooperation": 0.58,
        "specialisation": 0.72,
        "compassion": 0.65,
        "resilience": 0.82,           # primary driver — robust to edge cases
        "creativity": 0.55,
        "persistence": 0.88,          # primary driver — thorough review
        "differentiation_threshold": 0.60,
        "differentiation_min_energy": 0.38,
    },
    AgentRole.RADIOLOGIST: {
        "curiosity": 0.52,
        "risk_tolerance": 0.22,       # very low — measurement precision
        "cooperation": 0.55,
        "specialisation": 0.90,       # primary driver — imaging expertise
        "compassion": 0.58,
        "resilience": 0.62,
        "creativity": 0.48,
        "persistence": 0.85,          # primary driver — systematic review
        "differentiation_threshold": 0.58,
        "differentiation_min_energy": 0.38,
    },
    AgentRole.PATIENT_ADVOCATE: {
        "curiosity": 0.58,
        "risk_tolerance": 0.45,
        "cooperation": 0.88,          # primary driver — collaborative
        "specialisation": 0.55,
        "compassion": 0.95,           # primary driver — patient wellbeing
        "resilience": 0.72,
        "creativity": 0.52,
        "persistence": 0.72,
        "differentiation_threshold": 0.55,
        "differentiation_min_energy": 0.30,
    },
    AgentRole.EPIDEMIOLOGIST: {
        "curiosity": 0.85,            # primary driver — pattern discovery
        "risk_tolerance": 0.50,
        "cooperation": 0.65,
        "specialisation": 0.65,
        "compassion": 0.60,
        "resilience": 0.60,
        "creativity": 0.78,           # primary driver — hypothesis generation
        "persistence": 0.78,
        "differentiation_threshold": 0.62,
        "differentiation_min_energy": 0.32,
    },
}

# Standard deviation for trait sampling (keeps variation realistic)
_TRAIT_SIGMA = 0.08


def create_medical_genome(role: AgentRole, rng: random.Random | None = None) -> Genome:
    """
    Return a Genome instance with traits biased toward the given medical role.

    Traits are sampled from a Gaussian centred on the role's ideal value,
    then clamped to [0, 1].  This models the natural variation among
    practitioners — no two specialists are identical, but they share a
    recognisable trait profile.

    Parameters
    ----------
    role:
        Target medical role.  Must be one of the ExMorbus medical roles.
    rng:
        Seeded random instance for reproducibility.

    Raises
    ------
    ValueError
        If ``role`` is not in ``MEDICAL_ROLE_BIAS``.
    """
    if role not in MEDICAL_ROLE_BIAS:
        raise ValueError(
            f"Role {role!r} is not a medical role. "
            f"Available medical roles: {list(MEDICAL_ROLE_BIAS)}"
        )
    r = rng or random.Random()
    bias = MEDICAL_ROLE_BIAS[role]

    def sample(trait: str) -> float:
        return clamp(r.gauss(bias[trait], _TRAIT_SIGMA))

    return Genome(
        curiosity=sample("curiosity"),
        risk_tolerance=sample("risk_tolerance"),
        cooperation=sample("cooperation"),
        specialisation=sample("specialisation"),
        compassion=sample("compassion"),
        resilience=sample("resilience"),
        creativity=sample("creativity"),
        persistence=sample("persistence"),
        differentiation_threshold=clamp(r.gauss(bias["differentiation_threshold"], 0.04)),
        differentiation_min_energy=clamp(r.gauss(bias["differentiation_min_energy"], 0.04)),
    )


def all_medical_roles() -> list[AgentRole]:
    """Return all AgentRole values that have a medical genome profile."""
    return list(MEDICAL_ROLE_BIAS.keys())
