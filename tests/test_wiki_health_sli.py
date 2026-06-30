"""
tests/test_wiki_health_sli.py

Phase 2 (slice C) — surfacing knowledge-wiki lint/query health as observability
SLIs. All offline (deterministic cognition); no API keys. Covers each SLO's
meeting and breaching paths, the no-probe and empty-wiki edges, and determinism.
"""

from __future__ import annotations

from organic_agentic_autodev.knowledge_wiki import KnowledgeWiki, LLMWikiCognition
from organic_agentic_autodev.observability import (
    WikiHealthMonitor,
    build_wiki_health_sla,
)
from organic_agentic_autodev.observability.contracts import SLOStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _healthy_wiki() -> KnowledgeWiki:
    """Two linked, substantial pages — no lint findings (mirrors the lint test)."""
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits in the agent.\ncount: 8")
    wiki.ingest(
        "topic: Stem Cell\nThe stem cell reads its Genome before differentiating.\nstate: blank"
    )
    return wiki


class _GhostLinkProvider:
    """Yields a page linking to a slug that is never created → dangling link."""

    def generate(self, system: str, prompt: str) -> str:
        return (
            '{"pages": [{"slug": "alpha", "title": "Alpha", "action": "create", '
            '"body": "# Alpha\\nLinks to a page that does not exist.", '
            '"links": ["ghost"], "claims": {"k": "v"}, "contradictions": []}]}'
        )


# ---------------------------------------------------------------------------
# SLA shape
# ---------------------------------------------------------------------------

def test_wiki_health_sla_has_four_slos():
    sla = build_wiki_health_sla()
    names = {s.name for s in sla.slos}
    assert names == {
        "wiki_link_integrity",
        "wiki_orphan_rate",
        "wiki_contradiction_count",
        "query_grounding_rate",
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_healthy_wiki_is_compliant():
    monitor = WikiHealthMonitor(
        _healthy_wiki(),
        probe_questions=["how many traits does the genome encode?"],
    )
    report = monitor.evaluate()

    assert report["sla_compliant"]
    assert report["breached"] == 0
    evals = report["evaluations"]
    assert evals["wiki_link_integrity"].status == SLOStatus.MEETING
    assert evals["wiki_orphan_rate"].status == SLOStatus.MEETING
    assert evals["wiki_contradiction_count"].status == SLOStatus.MEETING
    assert evals["query_grounding_rate"].status == SLOStatus.MEETING


# ---------------------------------------------------------------------------
# Failure paths — one per lint/query dimension
# ---------------------------------------------------------------------------

def test_orphans_breach_orphan_rate_slo():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes traits.\ncount: 8")
    wiki.ingest("topic: Pathfinder\nGraph routing.\nedges: many")  # unrelated → orphans
    report = WikiHealthMonitor(wiki).evaluate()

    orphan = report["evaluations"]["wiki_orphan_rate"]
    assert orphan.sli_measurement.value == 1.0   # both pages orphaned
    assert orphan.status == SLOStatus.BREACHED
    assert not report["sla_compliant"]


def test_dangling_link_breaches_link_integrity_slo():
    wiki = KnowledgeWiki(cognition=LLMWikiCognition(provider=_GhostLinkProvider()))
    wiki.ingest("seed source — provider decides the page")
    report = WikiHealthMonitor(wiki).evaluate()

    integrity = report["evaluations"]["wiki_link_integrity"]
    assert integrity.sli_measurement.value == 0.0   # the only link dangles
    assert integrity.status == SLOStatus.BREACHED


def test_single_contradiction_is_at_risk():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Hydration\nstatus: active\ndetail: baseline reading recorded")
    wiki.ingest("topic: Hydration\nstatus: inactive")  # conflicting claim
    report = WikiHealthMonitor(wiki).evaluate()

    contra = report["evaluations"]["wiki_contradiction_count"]
    assert contra.sli_measurement.value == 1.0
    assert contra.status == SLOStatus.AT_RISK   # target 0, at_risk ≤ 2


def test_low_grounding_breaches_query_slo():
    wiki = _healthy_wiki()
    monitor = WikiHealthMonitor(
        wiki,
        # one grounds (genome), one does not → 0.5 < target 0.80
        probe_questions=["genome traits", "completely unrelated xylophone quasar"],
    )
    report = monitor.evaluate()

    grounding = report["evaluations"]["query_grounding_rate"]
    assert grounding.sli_measurement.value == 0.5
    assert grounding.status == SLOStatus.BREACHED


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

def test_no_probes_yields_insufficient_grounding_data():
    report = WikiHealthMonitor(_healthy_wiki()).evaluate()
    grounding = report["evaluations"]["query_grounding_rate"]
    assert grounding.status == SLOStatus.INSUFFICIENT_DATA
    # Excluded from compliance — a healthy wiki is still compliant without probes.
    assert report["sla_compliant"]


def test_empty_wiki_is_vacuously_compliant():
    report = WikiHealthMonitor(KnowledgeWiki()).evaluate()
    # Nothing to measure → every SLO INSUFFICIENT_DATA, none breached.
    assert report["breached"] == 0
    assert report["insufficient_data"] == 4
    assert report["sla_compliant"]


def test_measurement_is_deterministic():
    monitor = WikiHealthMonitor(_healthy_wiki(), probe_questions=["genome traits"])
    first = monitor.evaluate()["measurements"]
    second = monitor.evaluate()["measurements"]
    assert first == second


def test_dashboard_string_renders_after_evaluate():
    monitor = WikiHealthMonitor(_healthy_wiki())
    monitor.evaluate()
    dash = monitor.dashboard_string()
    assert "Knowledge-Wiki Health SLA" in dash
    assert "wiki_link_integrity" in dash
