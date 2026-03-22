"""
src/observability/sla.py

Pre-defined SLA for the medical oncology research ecosystem (ExMorbus).

The medical SLA consists of 8 SLOs spanning:
  P1 (critical / patient-safety):
    - Adverse event coverage  — 100% of agents monitored
    - Knowledge confidence floor — mean confidence ≥ 0.70
  P2 (high):
    - Niche fill rate         — ≥ 80% of niches filled by tick 100
    - Guideline adherence     — ≥ 90% of treatment records guideline-aligned
    - Knowledge growth        — ≥ 2 new records per 10 ticks
    - Consensus rate          — ≥ 60% of oncology records reviewed
  P3 (medium):
    - Organ viability         — ≥ 50% of organs viable at all times
    - Agent energy headroom   — ≥ 20% of energy pool remaining

Usage:
    from src.observability.sla import build_medical_sla
    sla = build_medical_sla()
"""

from __future__ import annotations

from src.observability.contracts import (
    SLAContractV0,
    SLIKind,
    SLIWindowKind,
    SLOComparison,
    SLODefinitionV0,
)
from src.utils.helpers import new_id


def build_medical_sla() -> SLAContractV0:
    """
    Build and return the standard medical oncology ecosystem SLA.

    Returns
    -------
    SLAContractV0
        A complete SLA with 8 SLOs spanning safety, quality, growth, and
        ecosystem health dimensions.
    """
    slos = [

        # ----------------------------------------------------------------
        # P1 — Patient-Safety Critical
        # ----------------------------------------------------------------

        SLODefinitionV0(
            slo_id="slo_adverse_event_coverage",
            name="adverse_event_coverage",
            description=(
                "100% of active agents must be reachable by a GUARDIAN or PHARMACOLOGIST cell "
                "via the slime mold network within 5 ticks. "
                "This ensures that all Grade 3/4 toxicity signals can be broadcast and acted on."
            ),
            sli_kind=SLIKind.ADVERSE_EVENT_COVERAGE,
            target_value=1.0,           # 100% agents have a safety observer reachable
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.85,     # AT_RISK below 85%
            window=SLIWindowKind.CURRENT,
            priority="P1",
            min_sample_size=1,
        ),

        SLODefinitionV0(
            slo_id="slo_knowledge_confidence_floor",
            name="knowledge_confidence_floor",
            description=(
                "Mean confidence of all knowledge records in the Mouseion must be ≥ 0.70. "
                "Records below this threshold carry unacceptable clinical uncertainty for "
                "oncological decision support."
            ),
            sli_kind=SLIKind.KNOWLEDGE_CONFIDENCE_MEAN,
            target_value=0.70,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.65,     # AT_RISK below 0.65
            window=SLIWindowKind.ALL_TIME,
            priority="P1",
            min_sample_size=3,          # need at least 3 records to measure
        ),

        # ----------------------------------------------------------------
        # P2 — High
        # ----------------------------------------------------------------

        SLODefinitionV0(
            slo_id="slo_niche_fill_rate",
            name="niche_fill_rate",
            description=(
                "At least 80% of all defined niches must be filled by any given tick. "
                "Unfilled niches represent unmet ecosystem needs — clinical tasks that are "
                "not being performed."
            ),
            sli_kind=SLIKind.NICHE_FILL_RATE,
            target_value=0.80,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.60,
            window=SLIWindowKind.CURRENT,
            priority="P2",
            min_sample_size=1,
        ),

        SLODefinitionV0(
            slo_id="slo_guideline_adherence",
            name="guideline_adherence_rate",
            description=(
                "At least 90% of treatment recommendation and protocol records in the Mouseion "
                "must carry a 'guideline' or 'treatment_recommendation' tag with confidence ≥ 0.75. "
                "Non-guideline-aligned recommendations represent patient safety risks."
            ),
            sli_kind=SLIKind.GUIDELINE_ADHERENCE_RATE,
            target_value=0.90,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.78,
            window=SLIWindowKind.ROLLING_50_TICKS,
            priority="P2",
            min_sample_size=2,
        ),

        SLODefinitionV0(
            slo_id="slo_knowledge_growth",
            name="knowledge_growth_rate",
            description=(
                "The ecosystem must produce at least 2 new knowledge records per 10 ticks. "
                "Stagnant knowledge growth indicates agents are failing to perform their "
                "core research and synthesis functions."
            ),
            sli_kind=SLIKind.KNOWLEDGE_GROWTH_RATE,
            target_value=2.0,           # records per 10 ticks
            comparison=SLOComparison.GTE,
            at_risk_threshold=1.0,
            window=SLIWindowKind.ROLLING_10_TICKS,
            priority="P2",
            min_sample_size=1,
        ),

        SLODefinitionV0(
            slo_id="slo_consensus_rate",
            name="consensus_rate",
            description=(
                "At least 60% of oncology knowledge records (tagged 'oncology') must have "
                "been produced by an agent with specialisation_score > 0.2, indicating "
                "peer-reviewed specialist output rather than undifferentiated noise."
            ),
            sli_kind=SLIKind.CONSENSUS_RATE,
            target_value=0.60,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.45,
            window=SLIWindowKind.ALL_TIME,
            priority="P2",
            min_sample_size=3,
        ),

        # ----------------------------------------------------------------
        # P3 — Medium
        # ----------------------------------------------------------------

        SLODefinitionV0(
            slo_id="slo_organ_viability",
            name="organ_viability_rate",
            description=(
                "At least 50% of registered organs must be viable (≥ MIN_ORGAN_SIZE cells) "
                "at all times. Organ dissolution indicates a failure of the ecosystem's "
                "self-organisation and resource allocation."
            ),
            sli_kind=SLIKind.ORGAN_VIABILITY_RATE,
            target_value=0.50,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.33,
            window=SLIWindowKind.CURRENT,
            priority="P3",
            min_sample_size=1,
        ),

        SLODefinitionV0(
            slo_id="slo_energy_headroom",
            name="energy_headroom",
            description=(
                "The ecosystem energy pool must retain at least 20% of its initial capacity "
                "(200 units from 1000 initial). A depleted energy pool starves agents and "
                "prevents new StemCell differentiation."
            ),
            sli_kind=SLIKind.ENERGY_HEADROOM,
            target_value=0.20,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.10,
            window=SLIWindowKind.CURRENT,
            priority="P3",
            min_sample_size=1,
        ),
    ]

    return SLAContractV0(
        sla_id=new_id("sla_"),
        name="Medical Oncology Research Ecosystem SLA",
        description=(
            "Service Level Agreement governing the quality, safety, and operational health "
            "of the ExMorbus oncological research ecosystem. "
            "Covers 8 SLOs across patient safety, knowledge quality, niche coverage, "
            "guideline adherence, knowledge growth, and ecosystem vitality. "
            "Compliance target: ≥ 99% of all SLOs met at every evaluation point."
        ),
        slos=slos,
        compliance_target=0.99,
        review_period_ticks=10,
    )
