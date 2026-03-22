"""
src/observability/tracker.py

SLITracker — real-time SLI measurement and SLO evaluation for the organic
agentic ecosystem.

The SLITracker is a passive observer that:
  1. Subscribes to Mouseion events (KNOWLEDGE_STORED, NICHE_FILLED,
     AGENT_DIED) to maintain rolling counters.
  2. On each `tick()` call, computes fresh SLI measurements from the
     Mouseion state and the Environment.
  3. Evaluates each SLO against its target and logs breaches.
  4. Emits DANGER events back to the Mouseion when P1 SLOs are breached.

Design: the tracker does NOT store observations inside the Mouseion — it
maintains its own lightweight ledger.  This avoids contaminating the
ecosystem's knowledge base with meta-observability noise.

Usage:
    from src.observability.tracker import SLITracker
    from src.observability.sla import build_medical_sla

    tracker = SLITracker(mouseion=m, environment=env, sla=build_medical_sla())
    ...
    for t in range(200):
        env.tick()
        report = tracker.tick()
        if report["breached_slos"]:
            print("SLO breach!", report["breached_slos"])
"""

from __future__ import annotations

import statistics
from collections import defaultdict, deque
from typing import TYPE_CHECKING

from src.mouseion.contracts import EventEnvelopeV0, EventKind
from src.observability.contracts import (
    SLAContractV0,
    SLIKind,
    SLIMeasurementV0,
    SLIWindowKind,
    SLOEvaluationV0,
    SLOStatus,
)
from src.utils.helpers import clamp, get_logger, new_id

if TYPE_CHECKING:
    from src.core.environment import Environment
    from src.mouseion.substrate import Mouseion
    from src.organisms.body import Body

logger = get_logger("observability.tracker")

# How many ticks of rolling history to keep
_ROLLING_WINDOW_SHORT = 10
_ROLLING_WINDOW_LONG  = 50


class SLITracker:
    """
    Real-time SLI measurement and SLO compliance evaluation.

    Parameters
    ----------
    mouseion:
        Shared knowledge substrate — source of truth for all knowledge-related
        SLIs.
    environment:
        Ecosystem environment — source for agent counts, niche state, energy.
    sla:
        The SLA contract whose SLOs we are evaluating.
    body:
        Optional Body instance — used for organ viability SLI.
    initial_energy:
        The initial energy pool size (used to compute energy headroom %).
    """

    def __init__(
        self,
        mouseion: "Mouseion",
        environment: "Environment",
        sla: SLAContractV0,
        body: "Body | None" = None,
        initial_energy: float = 1000.0,
    ) -> None:
        self._mouseion = mouseion
        self._environment = environment
        self._sla = sla
        self._body = body
        self._initial_energy = initial_energy

        # Rolling event counters
        self._knowledge_ticks: deque[int] = deque(maxlen=_ROLLING_WINDOW_SHORT)
        self._agent_deaths: deque[int] = deque(maxlen=_ROLLING_WINDOW_LONG)
        self._niches_filled: set[str] = set()

        # Knowledge baseline for growth rate calculation
        self._knowledge_count_last_window: int = 0
        self._tick = 0

        # Evaluation history (latest per SLO)
        self._latest_evaluations: dict[str, SLOEvaluationV0] = {}
        # Full history (capped)
        self._evaluation_history: list[SLOEvaluationV0] = []
        self._MAX_HISTORY = 1000

        # Subscribe to Mouseion events
        mouseion.subscribe(EventKind.KNOWLEDGE_STORED, self._on_knowledge_stored)
        mouseion.subscribe(EventKind.NICHE_FILLED, self._on_niche_filled)
        mouseion.subscribe(EventKind.AGENT_DIED, self._on_agent_died)

        logger.info(
            "SLITracker initialised for SLA '%s' with %d SLOs",
            sla.name, len(sla.slos),
        )

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    def _on_knowledge_stored(self, event: EventEnvelopeV0) -> None:
        """Track newly stored knowledge records."""
        # Count records per short window tick
        if self._knowledge_ticks:
            self._knowledge_ticks[-1] += 1
        else:
            self._knowledge_ticks.append(1)

    def _on_niche_filled(self, event: EventEnvelopeV0) -> None:
        niche_id = event.payload.get("niche_id", "")
        if niche_id:
            self._niches_filled.add(niche_id)

    def _on_agent_died(self, event: EventEnvelopeV0) -> None:
        if self._agent_deaths:
            self._agent_deaths[-1] += 1
        else:
            self._agent_deaths.append(1)

    # ------------------------------------------------------------------
    # SLI Measurement
    # ------------------------------------------------------------------

    def _measure_knowledge_confidence_mean(self) -> SLIMeasurementV0:
        records = list(self._mouseion.all_knowledge())
        if not records:
            return SLIMeasurementV0(
                measurement_id=new_id("sli_"),
                sli_kind=SLIKind.KNOWLEDGE_CONFIDENCE_MEAN,
                value=0.0,
                unit="confidence",
                tick=self._tick,
                window=SLIWindowKind.ALL_TIME,
                sample_size=0,
            )
        mean_conf = statistics.mean(r.confidence for r in records)
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.KNOWLEDGE_CONFIDENCE_MEAN,
            value=round(mean_conf, 4),
            unit="confidence",
            tick=self._tick,
            window=SLIWindowKind.ALL_TIME,
            sample_size=len(records),
        )

    def _measure_niche_fill_rate(self) -> SLIMeasurementV0:
        all_niches = self._environment._niches
        if not all_niches:
            rate = 1.0   # no niches = trivially all filled
        else:
            filled = sum(1 for n in all_niches.values() if not n.is_open)
            rate = filled / len(all_niches)
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.NICHE_FILL_RATE,
            value=round(rate, 4),
            unit="%",
            tick=self._tick,
            window=SLIWindowKind.CURRENT,
            sample_size=len(all_niches),
        )

    def _measure_adverse_event_coverage(self) -> SLIMeasurementV0:
        """
        Proxy: fraction of total agents that are safety-role (GUARDIAN or
        PHARMACOLOGIST) or are within proximity of one.  Simplified: if any
        GUARDIAN/PHARMACOLOGIST agent exists and there are agents alive,
        assume coverage proportional to safety-role density.
        """
        from src.mouseion.contracts import AgentRole
        agents = self._environment.all_agents()
        if not agents:
            return SLIMeasurementV0(
                measurement_id=new_id("sli_"),
                sli_kind=SLIKind.ADVERSE_EVENT_COVERAGE,
                value=1.0,
                unit="%",
                tick=self._tick,
                window=SLIWindowKind.CURRENT,
                sample_size=0,
            )
        safety_roles = {AgentRole.GUARDIAN, AgentRole.PHARMACOLOGIST, AgentRole.PATIENT_ADVOCATE}
        safety_agents = sum(1 for a in agents if a.role in safety_roles)
        # Each safety agent can cover up to 10 agents (neighbourhood model)
        coverage = min(1.0, (safety_agents * 10) / len(agents))
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.ADVERSE_EVENT_COVERAGE,
            value=round(coverage, 4),
            unit="%",
            tick=self._tick,
            window=SLIWindowKind.CURRENT,
            sample_size=len(agents),
        )

    def _measure_guideline_adherence(self) -> SLIMeasurementV0:
        """
        Fraction of treatment/protocol records that have confidence ≥ 0.75.
        These are records tagged 'treatment_protocol', 'treatment_recommendation',
        or 'guideline'.
        """
        qualified_tags = {"treatment_protocol", "treatment_recommendation", "guideline",
                          "oncology"}
        records = [
            r for r in self._mouseion.all_knowledge()
            if any(t in r.topic_tags for t in qualified_tags)
        ]
        if not records:
            return SLIMeasurementV0(
                measurement_id=new_id("sli_"),
                sli_kind=SLIKind.GUIDELINE_ADHERENCE_RATE,
                value=1.0,
                unit="%",
                tick=self._tick,
                window=SLIWindowKind.ROLLING_50_TICKS,
                sample_size=0,
            )
        adherent = sum(1 for r in records if r.confidence >= 0.75)
        rate = adherent / len(records)
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.GUIDELINE_ADHERENCE_RATE,
            value=round(rate, 4),
            unit="%",
            tick=self._tick,
            window=SLIWindowKind.ROLLING_50_TICKS,
            sample_size=len(records),
        )

    def _measure_knowledge_growth_rate(self) -> SLIMeasurementV0:
        """Records produced in the last 10 ticks."""
        current_count = self._mouseion.knowledge_count()
        growth = current_count - self._knowledge_count_last_window
        # Update baseline every 10 ticks
        if self._tick % _ROLLING_WINDOW_SHORT == 0:
            self._knowledge_count_last_window = current_count
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.KNOWLEDGE_GROWTH_RATE,
            value=float(max(growth, 0)),
            unit="records/10t",
            tick=self._tick,
            window=SLIWindowKind.ROLLING_10_TICKS,
            sample_size=1,
        )

    def _measure_consensus_rate(self) -> SLIMeasurementV0:
        """
        Fraction of oncology-tagged records authored by specialist cells.
        We use the record's author_id as a proxy: records NOT authored by
        the ExMorbus seeder are from agents (who start with low spec score
        and build it up).  We treat all agent-authored oncology records as
        having been through a specialist interaction.
        """
        from src.domain.exmorbus.seeder import EXMORBUS_SEED_AUTHOR
        oncology_records = [
            r for r in self._mouseion.all_knowledge()
            if "oncology" in r.topic_tags
        ]
        if not oncology_records:
            return SLIMeasurementV0(
                measurement_id=new_id("sli_"),
                sli_kind=SLIKind.CONSENSUS_RATE,
                value=0.0,
                unit="%",
                tick=self._tick,
                window=SLIWindowKind.ALL_TIME,
                sample_size=0,
            )
        # Count agent-authored (non-seed) records — these went through specialist processing
        agent_authored = sum(
            1 for r in oncology_records if r.author_id != EXMORBUS_SEED_AUTHOR
        )
        rate = agent_authored / len(oncology_records)
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.CONSENSUS_RATE,
            value=round(rate, 4),
            unit="%",
            tick=self._tick,
            window=SLIWindowKind.ALL_TIME,
            sample_size=len(oncology_records),
        )

    def _measure_organ_viability(self) -> SLIMeasurementV0:
        """Fraction of registered organs that are viable."""
        if self._body is None or not self._body._organs:
            return SLIMeasurementV0(
                measurement_id=new_id("sli_"),
                sli_kind=SLIKind.ORGAN_VIABILITY_RATE,
                value=1.0,   # no organs = trivially compliant
                unit="%",
                tick=self._tick,
                window=SLIWindowKind.CURRENT,
                sample_size=0,
            )
        total = len(self._body._organs)
        viable = sum(1 for o in self._body._organs.values() if o.is_viable)
        rate = viable / total
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.ORGAN_VIABILITY_RATE,
            value=round(rate, 4),
            unit="%",
            tick=self._tick,
            window=SLIWindowKind.CURRENT,
            sample_size=total,
        )

    def _measure_energy_headroom(self) -> SLIMeasurementV0:
        from src.mouseion.contracts import ResourceKind
        current = self._mouseion.resource_level(ResourceKind.ENERGY)
        headroom = clamp(current / self._initial_energy)
        return SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.ENERGY_HEADROOM,
            value=round(headroom, 4),
            unit="%",
            tick=self._tick,
            window=SLIWindowKind.CURRENT,
            sample_size=1,
        )

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self) -> dict:
        """
        Advance the tracker by one simulation tick.

        Computes all SLI measurements, evaluates all SLOs, records evaluations,
        and emits DANGER events for any P1 breaches.

        Returns a summary dict suitable for dashboard display.
        """
        self._tick += 1
        # Extend rolling counters each tick
        self._knowledge_ticks.append(0)
        self._agent_deaths.append(0)

        # --- Compute all SLI measurements ---
        measurements: dict[SLIKind, SLIMeasurementV0] = {
            SLIKind.KNOWLEDGE_CONFIDENCE_MEAN: self._measure_knowledge_confidence_mean(),
            SLIKind.NICHE_FILL_RATE:           self._measure_niche_fill_rate(),
            SLIKind.ADVERSE_EVENT_COVERAGE:    self._measure_adverse_event_coverage(),
            SLIKind.GUIDELINE_ADHERENCE_RATE:  self._measure_guideline_adherence(),
            SLIKind.KNOWLEDGE_GROWTH_RATE:     self._measure_knowledge_growth_rate(),
            SLIKind.CONSENSUS_RATE:            self._measure_consensus_rate(),
            SLIKind.ORGAN_VIABILITY_RATE:      self._measure_organ_viability(),
            SLIKind.ENERGY_HEADROOM:           self._measure_energy_headroom(),
        }

        # --- Evaluate SLOs ---
        evaluations: list[SLOEvaluationV0] = []
        breached: list[SLOEvaluationV0] = []
        at_risk: list[SLOEvaluationV0] = []

        for slo in self._sla.slos:
            measurement = measurements.get(slo.sli_kind)
            if measurement is None:
                continue

            status = slo.evaluate(measurement)

            if slo.comparison.value == "gte":
                delta = measurement.value - slo.target_value
            else:
                delta = slo.target_value - measurement.value

            msg = (
                f"[{status.value.upper()}] {slo.name} ({slo.priority}): "
                f"{slo.sli_kind.value}={measurement.value:.3f} "
                f"(target{'≥' if slo.comparison.value == 'gte' else '≤'}{slo.target_value:.3f}, "
                f"Δ={delta:+.3f})"
            )

            evaluation = SLOEvaluationV0(
                evaluation_id=new_id("eval_"),
                slo_id=slo.slo_id,
                slo_name=slo.name,
                slo_priority=slo.priority,
                sli_measurement=measurement,
                status=status,
                delta=delta,
                tick=self._tick,
                message=msg,
            )
            evaluations.append(evaluation)
            self._latest_evaluations[slo.slo_id] = evaluation
            self._evaluation_history.append(evaluation)

            if status == SLOStatus.BREACHED:
                breached.append(evaluation)
                if slo.priority == "P1":
                    self._emit_breach_event(evaluation)
            elif status == SLOStatus.AT_RISK:
                at_risk.append(evaluation)

        # Trim history
        if len(self._evaluation_history) > self._MAX_HISTORY:
            self._evaluation_history = self._evaluation_history[-self._MAX_HISTORY:]

        # --- Build summary ---
        # Exclude INSUFFICIENT_DATA from compliance denominator — these are
        # SLOs that cannot yet be evaluated (not enough data points).
        eligible_evals = [e for e in evaluations if e.status != SLOStatus.INSUFFICIENT_DATA]
        total_eligible = len(eligible_evals)
        meeting = sum(1 for e in eligible_evals if e.status == SLOStatus.MEETING)
        compliance = meeting / total_eligible if total_eligible else 1.0
        sla_compliant = compliance >= self._sla.compliance_target

        return {
            "tick": self._tick,
            "slos_evaluated": len(evaluations),
            "meeting": meeting,
            "at_risk": len(at_risk),
            "breached": len(breached),
            "compliance_rate": round(compliance, 4),
            "sla_compliant": sla_compliant,
            "breached_slos": [e.slo_name for e in breached],
            "at_risk_slos": [e.slo_name for e in at_risk],
            "measurements": {
                k.value: round(v.value, 4) for k, v in measurements.items()
            },
        }

    def _emit_breach_event(self, evaluation: SLOEvaluationV0) -> None:
        """Emit a Mouseion DANGER event when a P1 SLO is breached."""
        from src.slime_mold.signal import SignalType
        self._mouseion.emit(EventEnvelopeV0(
            event_id=new_id("evt_"),
            kind=EventKind.FITNESS_EVALUATED,
            source_agent_id="sli_tracker",
            payload={
                "slo_id": evaluation.slo_id,
                "slo_name": evaluation.slo_name,
                "status": "BREACHED",
                "value": evaluation.sli_measurement.value,
                "message": evaluation.message,
            },
        ))
        logger.warning("P1 SLO BREACHED: %s", evaluation.message)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def latest_report(self) -> dict[str, SLOEvaluationV0]:
        """Return the most recent evaluation for each SLO."""
        return dict(self._latest_evaluations)

    def slo_status(self, slo_id: str) -> SLOStatus | None:
        """Return the latest status of one SLO by ID."""
        ev = self._latest_evaluations.get(slo_id)
        return ev.status if ev else None

    def compliance_summary(self) -> dict:
        """Return a human-readable compliance report over all latest evaluations."""
        evals = list(self._latest_evaluations.values())
        if not evals:
            return {"message": "No evaluations yet"}

        by_status: dict[str, list[str]] = defaultdict(list)
        for e in evals:
            by_status[e.status.value].append(f"{e.slo_name} ({e.slo_priority}): {e.sli_measurement.value:.3f}")

        # Exclude INSUFFICIENT_DATA from compliance denominator
        eligible = [e for e in evals if e.status != SLOStatus.INSUFFICIENT_DATA]
        total = len(eligible)
        meeting = sum(1 for e in eligible if e.status == SLOStatus.MEETING)
        compliance = meeting / total if total else 1.0

        return {
            "total_slos": len(evals),
            "eligible_slos": total,
            "meeting": meeting,
            "at_risk": len(by_status.get("at_risk", [])),
            "breached": len(by_status.get("breached", [])),
            "insufficient_data": len(by_status.get("insufficient_data", [])),
            "compliance_rate": round(compliance, 4),
            "sla_compliant": compliance >= self._sla.compliance_target,
            "details": dict(by_status),
        }

    def dashboard_string(self) -> str:
        """Return a formatted ASCII dashboard of current SLO status."""
        STATUS_EMOJI = {
            "meeting": "✅",
            "at_risk": "⚠️ ",
            "breached": "🔴",
            "insufficient_data": "⏳",
        }
        lines = [
            f"{'─' * 70}",
            f"  SLA: {self._sla.name}",
            f"  Tick: {self._tick}  |  SLOs: {len(self._latest_evaluations)}",
            f"{'─' * 70}",
        ]
        for slo in self._sla.slos:
            ev = self._latest_evaluations.get(slo.slo_id)
            if ev is None:
                lines.append(f"  ⏳  [{slo.priority}] {slo.name:<40} — no data")
                continue
            icon = STATUS_EMOJI.get(ev.status.value, "?")
            lines.append(
                f"  {icon} [{slo.priority}] {slo.name:<40} "
                f"= {ev.sli_measurement.value:.3f}  (target "
                f"{'≥' if slo.comparison.value == 'gte' else '≤'}"
                f"{slo.target_value:.2f}, Δ={ev.delta:+.3f})"
            )
        lines.append(f"{'─' * 70}")
        summary = self.compliance_summary()
        eligible = summary.get("eligible_slos", summary.get("total_slos", 0))
        lines.append(
            f"  Overall: {summary.get('meeting', 0)}/{eligible} eligible SLOs meeting  "
            f"| Compliance: {summary.get('compliance_rate', 0):.1%}  "
            f"| SLA {'✅ COMPLIANT' if summary.get('sla_compliant') else '🔴 BREACHED'}"
        )
        if summary.get("insufficient_data", 0):
            lines.append(
                f"  ⏳ {summary['insufficient_data']} SLOs pending sufficient data (excluded from compliance)"
            )
        lines.append(f"{'─' * 70}")
        return "\n".join(lines)
