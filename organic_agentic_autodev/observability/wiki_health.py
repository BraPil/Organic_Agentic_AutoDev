"""
organic_agentic_autodev/observability/wiki_health.py

Surfaces the compounding knowledge wiki's health as observability SLIs.

Phase 1 built Karpathy's ``lint`` (structural health) and ``query`` (grounded
retrieval) over the Mouseion. This module makes those *measurable* against the
existing SLI/SLO framework, so wiki decay is observable rather than anecdotal —
honoring the top constitution value (Observability: if it isn't measured, it
doesn't exist).

Design mirrors ``SLITracker``: a **passive observer**. It reads a
``KnowledgeWiki``, runs ``lint()`` once plus a fixed set of probe questions
through ``query()``, derives ``SLIMeasurementV0`` values, and evaluates them
against an ``SLAContractV0`` of wiki-health SLOs. It writes nothing back — measuring
health must not mutate the thing being measured (so probe queries use
``promote=False``).

Determinism: ``lint`` is already deterministic, and retrieval is deterministic
lexical overlap, so two evaluations of an unchanged wiki produce identical SLI
values. No new dependency; fully offline.

Four indicators (the structural ``lint`` findings collapse to three actionable
SLIs; ``query`` contributes one). ``stubs`` are intentionally advisory only —
an under-developed page is a nudge, not a health breach — so they are reported by
``lint`` but not gated by an SLO here.

    from organic_agentic_autodev.observability.wiki_health import WikiHealthMonitor
    monitor = WikiHealthMonitor(wiki, probe_questions=["how many traits?"])
    report = monitor.evaluate()
    print(monitor.dashboard_string())
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from organic_agentic_autodev.observability.contracts import (
    SLAContractV0,
    SLIKind,
    SLIMeasurementV0,
    SLIWindowKind,
    SLOComparison,
    SLODefinitionV0,
    SLOEvaluationV0,
    SLOStatus,
)
from organic_agentic_autodev.utils.helpers import get_logger, new_id

if TYPE_CHECKING:
    from organic_agentic_autodev.knowledge_wiki.wiki import KnowledgeWiki

logger = get_logger("observability.wiki_health")


# ---------------------------------------------------------------------------
# SLA definition (flesh) — the wiki-health objectives
# ---------------------------------------------------------------------------

def build_wiki_health_sla() -> SLAContractV0:
    """
    Build the standard knowledge-wiki health SLA.

    Defaults are deliberately strict on integrity (any dangling link is a real
    defect) and lenient-with-warning on orphans/contradictions (they signal work
    to do, not corruption). Consumers tune the targets to their tolerance.
    """
    slos = [
        SLODefinitionV0(
            slo_id="slo_wiki_link_integrity",
            name="wiki_link_integrity",
            description=(
                "Every cross-reference in the wiki must resolve to a real page. "
                "Dangling links (and the missing concepts behind them) break "
                "navigation and signal half-finished synthesis."
            ),
            sli_kind=SLIKind.WIKI_LINK_INTEGRITY,
            target_value=1.0,            # all links resolve
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.90,
            window=SLIWindowKind.CURRENT,
            priority="P2",
            min_sample_size=1,           # need ≥1 link to measure integrity
        ),
        SLODefinitionV0(
            slo_id="slo_wiki_orphan_rate",
            name="wiki_orphan_rate",
            description=(
                "Fraction of pages disconnected from the link graph. Orphans are "
                "knowledge the wiki cannot reach by navigation — a cross-referencing "
                "gap rather than a correctness failure."
            ),
            sli_kind=SLIKind.WIKI_ORPHAN_RATE,
            target_value=0.0,
            comparison=SLOComparison.LTE,
            at_risk_threshold=0.25,
            window=SLIWindowKind.CURRENT,
            priority="P3",
            min_sample_size=1,
        ),
        SLODefinitionV0(
            slo_id="slo_wiki_contradiction_count",
            name="wiki_contradiction_count",
            description=(
                "Count of unresolved claim conflicts (same key, different value) "
                "surfaced by ingest's flag-and-keep policy. Each one is a decision a "
                "human or a future resolver still owes the wiki."
            ),
            sli_kind=SLIKind.WIKI_CONTRADICTION_COUNT,
            target_value=0.0,            # zero outstanding conflicts
            comparison=SLOComparison.LTE,
            at_risk_threshold=2.0,       # 1–2 pending = warn, ≥3 = breach
            window=SLIWindowKind.CURRENT,
            priority="P2",
            min_sample_size=1,
        ),
        SLODefinitionV0(
            slo_id="slo_query_grounding_rate",
            name="query_grounding_rate",
            description=(
                "Fraction of probe questions that retrieve at least one wiki page. "
                "A low rate means the wiki cannot answer questions it should — the "
                "baseline against which a future vector-retrieval upgrade is judged."
            ),
            sli_kind=SLIKind.QUERY_GROUNDING_RATE,
            target_value=0.80,
            comparison=SLOComparison.GTE,
            at_risk_threshold=0.60,
            window=SLIWindowKind.CURRENT,
            priority="P2",
            min_sample_size=1,           # no probes → INSUFFICIENT_DATA
        ),
    ]
    return SLAContractV0(
        sla_id=new_id("sla_"),
        name="Knowledge-Wiki Health SLA",
        description=(
            "Service Level Agreement governing the structural health and "
            "retrievability of the compounding knowledge wiki. Covers link "
            "integrity, orphan rate, unresolved contradictions, and query "
            "grounding. Compliance target: ≥ 99% of eligible SLOs met."
        ),
        slos=slos,
        compliance_target=0.99,
        review_period_ticks=1,
    )


# ---------------------------------------------------------------------------
# Monitor (flesh) — passive observer over a KnowledgeWiki
# ---------------------------------------------------------------------------

class WikiHealthMonitor:
    """
    Evaluate a ``KnowledgeWiki``'s health against an ``SLAContractV0``.

    Parameters
    ----------
    wiki:
        The wiki to observe. Never mutated by this monitor.
    sla:
        The objectives to evaluate against. Defaults to ``build_wiki_health_sla()``.
    probe_questions:
        Representative questions used to measure query grounding. With none
        supplied, the grounding SLO reports INSUFFICIENT_DATA (and is excluded
        from compliance) rather than guessing.
    """

    def __init__(
        self,
        wiki: KnowledgeWiki,
        *,
        sla: SLAContractV0 | None = None,
        probe_questions: list[str] | None = None,
    ) -> None:
        self._wiki = wiki
        self._sla = sla or build_wiki_health_sla()
        self._probes = [q for q in (probe_questions or []) if q and q.strip()]
        self._latest_evaluations: dict[str, SLOEvaluationV0] = {}

    # ------------------------------------------------------------------
    # SLI measurement
    # ------------------------------------------------------------------

    def measure(self) -> dict[SLIKind, SLIMeasurementV0]:
        """Compute the four wiki-health SLI measurements from a single lint pass."""
        report = self._wiki.lint()
        pages = self._wiki.pages()
        page_count = len(pages)
        total_links = sum(len(p.links) for p in pages)

        # Link integrity: fraction of links that resolve. No links → nothing to
        # measure (sample_size 0 → INSUFFICIENT_DATA), not a vacuous "perfect".
        integrity = (
            1.0 - len(report.dangling_links) / total_links if total_links else 1.0
        )
        link_integrity = SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.WIKI_LINK_INTEGRITY,
            value=round(integrity, 4),
            unit="%",
            tick=0,
            window=SLIWindowKind.CURRENT,
            sample_size=total_links,
        )

        orphan_rate = SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.WIKI_ORPHAN_RATE,
            value=round(len(report.orphans) / page_count, 4) if page_count else 0.0,
            unit="%",
            tick=0,
            window=SLIWindowKind.CURRENT,
            sample_size=page_count,
        )

        contradiction_count = SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.WIKI_CONTRADICTION_COUNT,
            value=float(len(report.contradictions)),
            unit="count",
            tick=0,
            window=SLIWindowKind.CURRENT,
            sample_size=page_count,
        )

        # Grounding: probe questions that retrieve ≥1 page. promote=False so the
        # act of measuring never writes answers back into the store.
        if self._probes:
            grounded = sum(
                1 for q in self._probes if self._wiki.query(q, promote=False).grounded
            )
            grounding = grounded / len(self._probes)
        else:
            grounding = 1.0
        grounding_rate = SLIMeasurementV0(
            measurement_id=new_id("sli_"),
            sli_kind=SLIKind.QUERY_GROUNDING_RATE,
            value=round(grounding, 4),
            unit="%",
            tick=0,
            window=SLIWindowKind.CURRENT,
            sample_size=len(self._probes),
        )

        return {
            SLIKind.WIKI_LINK_INTEGRITY: link_integrity,
            SLIKind.WIKI_ORPHAN_RATE: orphan_rate,
            SLIKind.WIKI_CONTRADICTION_COUNT: contradiction_count,
            SLIKind.QUERY_GROUNDING_RATE: grounding_rate,
        }

    # ------------------------------------------------------------------
    # SLO evaluation
    # ------------------------------------------------------------------

    def evaluate(self, tick: int = 0) -> dict:
        """
        Measure SLIs, evaluate every SLO, and return a compliance summary.

        INSUFFICIENT_DATA SLOs are excluded from the compliance denominator —
        an unmeasurable objective is neither met nor breached (same convention as
        ``SLITracker``).
        """
        measurements = self.measure()
        evaluations: dict[str, SLOEvaluationV0] = {}
        breached: list[str] = []
        at_risk: list[str] = []

        for slo in self._sla.slos:
            measurement = measurements.get(slo.sli_kind)
            if measurement is None:
                continue
            status = slo.evaluate(measurement)
            if slo.comparison == SLOComparison.GTE:
                delta = measurement.value - slo.target_value
            else:
                delta = slo.target_value - measurement.value
            evaluation = SLOEvaluationV0(
                evaluation_id=new_id("eval_"),
                slo_id=slo.slo_id,
                slo_name=slo.name,
                slo_priority=slo.priority,
                sli_measurement=measurement,
                status=status,
                delta=delta,
                tick=tick,
                message=(
                    f"[{status.value.upper()}] {slo.name} ({slo.priority}): "
                    f"{slo.sli_kind.value}={measurement.value:.3f}"
                ),
            )
            evaluations[slo.name] = evaluation
            self._latest_evaluations[slo.slo_id] = evaluation
            if status == SLOStatus.BREACHED:
                breached.append(slo.name)
            elif status == SLOStatus.AT_RISK:
                at_risk.append(slo.name)

        eligible = [
            e for e in evaluations.values()
            if e.status != SLOStatus.INSUFFICIENT_DATA
        ]
        meeting = sum(1 for e in eligible if e.status == SLOStatus.MEETING)
        compliance = meeting / len(eligible) if eligible else 1.0
        summary = {
            "tick": tick,
            "slos_evaluated": len(evaluations),
            "meeting": meeting,
            "at_risk": len(at_risk),
            "breached": len(breached),
            "insufficient_data": len(evaluations) - len(eligible),
            "compliance_rate": round(compliance, 4),
            "sla_compliant": compliance >= self._sla.compliance_target,
            "breached_slos": breached,
            "at_risk_slos": at_risk,
            "measurements": {k.value: round(v.value, 4) for k, v in measurements.items()},
            "evaluations": evaluations,
        }
        logger.info(
            "wiki health → %d/%d eligible SLOs meeting (%.0f%%), %d breached",
            meeting, len(eligible), compliance * 100, len(breached),
        )
        return summary

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------

    def dashboard_string(self) -> str:
        """Formatted ASCII dashboard of the latest wiki-health evaluation."""
        STATUS_EMOJI = {
            "meeting": "✅",
            "at_risk": "⚠️ ",
            "breached": "🔴",
            "insufficient_data": "⏳",
        }
        lines = [
            f"{'─' * 70}",
            f"  {self._sla.name}",
            f"{'─' * 70}",
        ]
        for slo in self._sla.slos:
            ev = self._latest_evaluations.get(slo.slo_id)
            if ev is None:
                lines.append(f"  ⏳  [{slo.priority}] {slo.name:<32} — not yet evaluated")
                continue
            icon = STATUS_EMOJI.get(ev.status.value, "?")
            lines.append(
                f"  {icon} [{slo.priority}] {slo.name:<32} "
                f"= {ev.sli_measurement.value:.3f}  (target "
                f"{'≥' if slo.comparison.value == 'gte' else '≤'}"
                f"{slo.target_value:.2f}, Δ={ev.delta:+.3f})"
            )
        lines.append(f"{'─' * 70}")
        return "\n".join(lines)
