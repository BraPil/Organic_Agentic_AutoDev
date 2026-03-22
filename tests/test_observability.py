"""
tests/test_observability.py — Tests for the SLA/SLO/SLI observability layer.

Covers:
  - SLODefinitionV0.evaluate() — all comparison directions and status transitions
  - SLAContractV0 structure and SLO lookup
  - SLITracker: tick computation, SLO evaluation, breach detection
  - build_medical_sla() — 8 SLOs, correct priorities, valid targets
  - compliance_summary() and dashboard_string()
"""

from __future__ import annotations

import random

import pytest

from src.core.environment import Environment
from src.domain.exmorbus.niches import create_medical_niches
from src.domain.exmorbus.seeder import seed_mouseion
from src.mouseion.contracts import AgentRole, ResourceKind
from src.mouseion.substrate import Mouseion
from src.observability.contracts import (
    SLAContractV0,
    SLIKind,
    SLIMeasurementV0,
    SLIWindowKind,
    SLOComparison,
    SLODefinitionV0,
    SLOStatus,
)
from src.observability.sla import build_medical_sla
from src.observability.tracker import SLITracker
from src.organisms.cell import Cell
from src.organisms.body import Body
from src.organisms.organ import Organ
from src.utils.helpers import new_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_measurement(kind: SLIKind, value: float, sample_size: int = 5) -> SLIMeasurementV0:
    return SLIMeasurementV0(
        measurement_id=new_id("sli_"),
        sli_kind=kind,
        value=value,
        unit="%",
        tick=1,
        window=SLIWindowKind.CURRENT,
        sample_size=sample_size,
    )


def _make_slo(
    target: float,
    comparison: SLOComparison,
    at_risk: float,
    kind: SLIKind = SLIKind.KNOWLEDGE_CONFIDENCE_MEAN,
) -> SLODefinitionV0:
    return SLODefinitionV0(
        slo_id=new_id("slo_"),
        name="test_slo",
        description="test",
        sli_kind=kind,
        target_value=target,
        comparison=comparison,
        at_risk_threshold=at_risk,
        window=SLIWindowKind.CURRENT,
        min_sample_size=1,
    )


def make_tracker_env(seed: int = 0) -> tuple[Mouseion, Environment, SLITracker]:
    mouseion = Mouseion()
    seed_mouseion(mouseion)
    niches = create_medical_niches()
    rng = random.Random(seed)
    env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
    env.seed_niches(niches)
    sla = build_medical_sla()
    tracker = SLITracker(mouseion=mouseion, environment=env, sla=sla)
    return mouseion, env, tracker


# ---------------------------------------------------------------------------
# SLODefinitionV0.evaluate()
# ---------------------------------------------------------------------------

class TestSLOEvaluation:
    # GTE comparisons
    def test_gte_meeting_when_above_target(self):
        slo = _make_slo(target=0.75, comparison=SLOComparison.GTE, at_risk=0.65)
        m = _make_measurement(SLIKind.KNOWLEDGE_CONFIDENCE_MEAN, 0.82)
        assert slo.evaluate(m) == SLOStatus.MEETING

    def test_gte_meeting_when_exactly_at_target(self):
        slo = _make_slo(target=0.75, comparison=SLOComparison.GTE, at_risk=0.65)
        m = _make_measurement(SLIKind.KNOWLEDGE_CONFIDENCE_MEAN, 0.75)
        assert slo.evaluate(m) == SLOStatus.MEETING

    def test_gte_at_risk_when_between_thresholds(self):
        slo = _make_slo(target=0.75, comparison=SLOComparison.GTE, at_risk=0.65)
        m = _make_measurement(SLIKind.KNOWLEDGE_CONFIDENCE_MEAN, 0.70)
        assert slo.evaluate(m) == SLOStatus.AT_RISK

    def test_gte_breached_when_below_at_risk(self):
        slo = _make_slo(target=0.75, comparison=SLOComparison.GTE, at_risk=0.65)
        m = _make_measurement(SLIKind.KNOWLEDGE_CONFIDENCE_MEAN, 0.50)
        assert slo.evaluate(m) == SLOStatus.BREACHED

    # LTE comparisons
    def test_lte_meeting_when_below_target(self):
        slo = _make_slo(target=10.0, comparison=SLOComparison.LTE, at_risk=12.0,
                        kind=SLIKind.CASE_SYNTHESIS_LATENCY)
        m = _make_measurement(SLIKind.CASE_SYNTHESIS_LATENCY, 8.0)
        assert slo.evaluate(m) == SLOStatus.MEETING

    def test_lte_breached_when_above_at_risk(self):
        slo = _make_slo(target=10.0, comparison=SLOComparison.LTE, at_risk=12.0,
                        kind=SLIKind.CASE_SYNTHESIS_LATENCY)
        m = _make_measurement(SLIKind.CASE_SYNTHESIS_LATENCY, 15.0)
        assert slo.evaluate(m) == SLOStatus.BREACHED

    # Insufficient data
    def test_insufficient_data_when_sample_too_small(self):
        slo = _make_slo(target=0.75, comparison=SLOComparison.GTE, at_risk=0.65)
        slo2 = SLODefinitionV0(
            slo_id=slo.slo_id,
            name=slo.name,
            description=slo.description,
            sli_kind=slo.sli_kind,
            target_value=slo.target_value,
            comparison=slo.comparison,
            at_risk_threshold=slo.at_risk_threshold,
            min_sample_size=10,
        )
        m = _make_measurement(SLIKind.KNOWLEDGE_CONFIDENCE_MEAN, 0.80, sample_size=2)
        assert slo2.evaluate(m) == SLOStatus.INSUFFICIENT_DATA


# ---------------------------------------------------------------------------
# SLAContractV0
# ---------------------------------------------------------------------------

class TestSLAContract:
    def setup_method(self):
        self.sla = build_medical_sla()

    def test_sla_has_8_slos(self):
        assert len(self.sla.slos) == 8

    def test_sla_has_p1_slos(self):
        p1s = self.sla.p1_slos()
        assert len(p1s) >= 2, "Expected at least 2 P1 (critical) SLOs"

    def test_sla_has_p2_slos(self):
        p2s = self.sla.p2_slos()
        assert len(p2s) >= 3

    def test_slo_by_id_returns_correct_slo(self):
        first = self.sla.slos[0]
        found = self.sla.slo_by_id(first.slo_id)
        assert found is not None
        assert found.slo_id == first.slo_id

    def test_slo_by_id_returns_none_for_unknown(self):
        assert self.sla.slo_by_id("nonexistent_slo") is None

    def test_all_slos_have_valid_targets(self):
        for slo in self.sla.slos:
            assert 0.0 <= slo.target_value <= 100.0

    def test_compliance_target_high(self):
        assert self.sla.compliance_target >= 0.95

    def test_adverse_event_slo_is_p1(self):
        ae_slo = self.sla.slo_by_id("slo_adverse_event_coverage")
        assert ae_slo is not None
        assert ae_slo.priority == "P1"

    def test_knowledge_confidence_slo_is_p1(self):
        conf_slo = self.sla.slo_by_id("slo_knowledge_confidence_floor")
        assert conf_slo is not None
        assert conf_slo.priority == "P1"


# ---------------------------------------------------------------------------
# SLITracker
# ---------------------------------------------------------------------------

class TestSLITrackerInitialState:
    def setup_method(self):
        self.mouseion, self.env, self.tracker = make_tracker_env(seed=10)

    def test_tick_returns_dict(self):
        report = self.tracker.tick()
        assert isinstance(report, dict)

    def test_tick_has_required_fields(self):
        report = self.tracker.tick()
        for field in ("tick", "slos_evaluated", "meeting", "at_risk", "breached",
                      "compliance_rate", "sla_compliant", "measurements"):
            assert field in report, f"Missing field: {field}"

    def test_slos_evaluated_count_matches_sla(self):
        report = self.tracker.tick()
        assert report["slos_evaluated"] == len(self.tracker._sla.slos)

    def test_compliance_rate_in_valid_range(self):
        report = self.tracker.tick()
        assert 0.0 <= report["compliance_rate"] <= 1.0

    def test_measurements_populated(self):
        report = self.tracker.tick()
        assert len(report["measurements"]) > 0


class TestSLITrackerWithSeededMouseion:
    """Tests with a seeded Mouseion — high-confidence records improve SLO scores."""

    def setup_method(self):
        self.mouseion, self.env, self.tracker = make_tracker_env(seed=42)

    def test_knowledge_confidence_high_after_seeding(self):
        self.tracker.tick()
        m = self.tracker._latest_evaluations.get("slo_knowledge_confidence_floor")
        assert m is not None
        assert m.sli_measurement.value >= 0.70, (
            f"Expected confidence ≥ 0.70 after seeding, got {m.sli_measurement.value}"
        )

    def test_knowledge_confidence_slo_meeting(self):
        self.tracker.tick()
        status = self.tracker.slo_status("slo_knowledge_confidence_floor")
        assert status == SLOStatus.MEETING

    def test_energy_headroom_meeting_initially(self):
        self.tracker.tick()
        status = self.tracker.slo_status("slo_energy_headroom")
        assert status == SLOStatus.MEETING

    def test_compliance_summary_structure(self):
        self.tracker.tick()
        summary = self.tracker.compliance_summary()
        assert "total_slos" in summary
        assert "meeting" in summary
        assert "compliance_rate" in summary
        assert "sla_compliant" in summary
        assert summary["total_slos"] == len(self.tracker._sla.slos)

    def test_dashboard_string_contains_slo_names(self):
        self.tracker.tick()
        dashboard = self.tracker.dashboard_string()
        assert "knowledge_confidence_floor" in dashboard
        assert "adverse_event_coverage" in dashboard
        assert "niche_fill_rate" in dashboard


class TestSLITrackerWithAgents:
    """Tests with agents running in the ecosystem."""

    def setup_method(self):
        mouseion = Mouseion(initial_resources={k: 2000.0 for k in ResourceKind})
        seed_mouseion(mouseion)
        niches = create_medical_niches()
        rng = random.Random(55)
        env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
        env.seed_niches(niches)
        self.mouseion = mouseion
        self.env = env

        from src.domain.exmorbus.genome_profiles import create_medical_genome
        from src.core.genome import Genome
        # Register a mix of medical cells; GUARDIAN uses standard genome
        medical_roles = [AgentRole.ONCOLOGIST, AgentRole.PATHOLOGIST,
                         AgentRole.GENETICIST, AgentRole.PHARMACOLOGIST]
        for role in medical_roles:
            genome = create_medical_genome(role, rng=random.Random(99))
            cell = Cell(role=role, genome=genome, initial_energy=50.0, rng=random.Random(0))
            env.register(cell)
        # Add a GUARDIAN with standard genome for adverse event coverage
        guardian_genome = Genome(resilience=0.9, compassion=0.85, persistence=0.8,
                                 cooperation=0.7, curiosity=0.5, risk_tolerance=0.3,
                                 specialisation=0.5, creativity=0.4)
        cell = Cell(role=AgentRole.GUARDIAN, genome=guardian_genome, initial_energy=50.0,
                    rng=random.Random(0))
        env.register(cell)

        sla = build_medical_sla()
        self.tracker = SLITracker(mouseion=mouseion, environment=env, sla=sla)

    def test_knowledge_grows_after_agent_steps(self):
        initial_count = self.mouseion.knowledge_count()
        for _ in range(30):
            self.env.tick()
        assert self.mouseion.knowledge_count() > initial_count

    def test_adverse_event_coverage_improves_with_safety_agents(self):
        report = self.tracker.tick()
        # GUARDIAN and PHARMACOLOGIST agents should provide coverage
        coverage = report["measurements"].get(SLIKind.ADVERSE_EVENT_COVERAGE.value, 0)
        assert coverage > 0.0, "Expected non-zero coverage with safety agents"

    def test_multiple_ticks_without_error(self):
        for t in range(20):
            report = self.tracker.tick()
            assert report["tick"] == t + 1

    def test_latest_report_populated_after_tick(self):
        self.tracker.tick()
        report = self.tracker.latest_report()
        assert len(report) == len(self.tracker._sla.slos)


class TestSLITrackerWithOrgans:
    """Tests with organs registered to Body — tests organ viability SLI."""

    def setup_method(self):
        mouseion = Mouseion()
        seed_mouseion(mouseion)
        niches = create_medical_niches()
        rng = random.Random(33)
        env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
        env.seed_niches(niches)
        self.mouseion = mouseion
        self.env = env

        self.body = Body("TestBody")
        # Create two viable organs
        cells_a = [Cell(role=AgentRole.ONCOLOGIST, initial_energy=20.0) for _ in range(2)]
        cells_b = [Cell(role=AgentRole.PATHOLOGIST, initial_energy=20.0) for _ in range(2)]
        for c in cells_a + cells_b:
            env.register(c)
        organ_a = Organ(founding_cells=cells_a)
        organ_b = Organ(founding_cells=cells_b)
        self.body.register_organ(organ_a)
        self.body.register_organ(organ_b)

        sla = build_medical_sla()
        self.tracker = SLITracker(
            mouseion=mouseion, environment=env, sla=sla, body=self.body
        )

    def test_organ_viability_meeting_with_two_viable_organs(self):
        self.tracker.tick()
        status = self.tracker.slo_status("slo_organ_viability")
        assert status in (SLOStatus.MEETING, SLOStatus.INSUFFICIENT_DATA), (
            f"Expected MEETING, got {status}"
        )

    def test_organ_viability_measurement_sample_size(self):
        self.tracker.tick()
        ev = self.tracker._latest_evaluations.get("slo_organ_viability")
        assert ev is not None
        assert ev.sli_measurement.sample_size == 2  # two organs registered
