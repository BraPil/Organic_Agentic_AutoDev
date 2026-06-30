"""
tests/test_knowledge_wiki_query_lint.py

Phase 1 — knowledge-wiki query + lint (P1.3). All offline (deterministic
cognition); no API keys. Covers retrieval ranking, answer promotion, the
empty-question failure path, and every lint finding.
"""

from __future__ import annotations

import pytest

from organic_agentic_autodev.knowledge_wiki import (
    KnowledgeWiki,
    LLMWikiCognition,
    relevance,
    tokenize,
)

# ---------------------------------------------------------------------------
# Retrieval primitives
# ---------------------------------------------------------------------------

def test_tokenize_drops_stopwords_and_short_tokens():
    toks = tokenize("The Genome encodes traits in [0, 1]")
    assert "genome" in toks
    assert "encodes" in toks
    assert "the" not in toks  # stopword
    assert "in" not in toks   # too short


def test_relevance_prefers_title_match():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes behavioural tendencies.")
    wiki.ingest("topic: Pathfinder\nGraph conductance and routing.")

    genome = wiki.page("genome")
    pathfinder = wiki.page("pathfinder")
    assert relevance("how does the genome work", genome) > relevance(
        "how does the genome work", pathfinder
    )


def test_relevance_zero_when_no_overlap():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes behavioural tendencies.")
    assert relevance("xylophone quasar", wiki.page("genome")) == 0.0


# ---------------------------------------------------------------------------
# Query — happy path
# ---------------------------------------------------------------------------

def _seed(wiki: KnowledgeWiki) -> None:
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits.\ntrait_count: 8")
    wiki.ingest("topic: Pathfinder\nNetworkX graph routing.\nconductance: 0.01-1.0")


def test_query_returns_relevant_pages_ranked():
    wiki = KnowledgeWiki()
    _seed(wiki)
    result = wiki.query("how many traits does the genome encode?")

    assert result.grounded
    assert result.pages[0] == "genome"  # most relevant first
    assert "trait_count=8" in result.answer


def test_query_promotes_grounded_answer_to_store():
    wiki = KnowledgeWiki()
    _seed(wiki)
    result = wiki.query("genome traits")

    assert result.promoted_record_id is not None
    answers = wiki.mouseion.query_knowledge(KnowledgeWiki.ANSWER_TAG)
    assert len(answers) == 1
    assert answers[0].record_id == result.promoted_record_id
    # The promoted answer carries provenance back to the source it drew on.
    assert answers[0].provenance_refs


def test_query_can_skip_promotion():
    wiki = KnowledgeWiki()
    _seed(wiki)
    result = wiki.query("genome traits", promote=False)

    assert result.promoted_record_id is None
    assert wiki.mouseion.query_knowledge(KnowledgeWiki.ANSWER_TAG) == []


def test_query_with_no_match_is_ungrounded_and_not_promoted():
    wiki = KnowledgeWiki()
    _seed(wiki)
    result = wiki.query("completely unrelated xylophone topic")

    assert not result.grounded
    assert result.pages == []
    assert result.promoted_record_id is None
    assert "No relevant" in result.answer


@pytest.mark.parametrize("bad", ["", "   "])
def test_empty_question_raises(bad):
    wiki = KnowledgeWiki()
    _seed(wiki)
    with pytest.raises(ValueError, match="empty question"):
        wiki.query(bad)


def test_query_respects_k_limit():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Alpha\nshared term cell.")
    wiki.ingest("topic: Beta\nshared term cell.")
    wiki.ingest("topic: Gamma\nshared term cell.")
    result = wiki.query("cell", k=2)
    assert len(result.pages) == 2


# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

def test_lint_healthy_when_linked_and_substantial():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits in the agent.\ncount: 8")
    wiki.ingest(
        "topic: Stem Cell\nThe stem cell reads its Genome before differentiating.\nstate: blank"
    )
    report = wiki.lint()
    # stem-cell links to genome; both have claims and bodies → no findings.
    assert report.healthy, report.summary()
    assert report.page_count == 2


def test_lint_detects_orphans():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes traits.\ncount: 8")
    wiki.ingest("topic: Pathfinder\nGraph routing.\nedges: many")  # unrelated, no link
    report = wiki.lint()
    assert set(report.orphans) == {"genome", "pathfinder"}
    assert not report.healthy


def test_lone_page_is_not_an_orphan():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits.\ncount: 8")
    report = wiki.lint()
    assert report.orphans == []


def test_lint_detects_contradictions():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Hydration\nstatus: active\ndetail: baseline reading recorded")
    wiki.ingest("topic: Hydration\nstatus: inactive")
    report = wiki.lint()
    assert len(report.contradictions) == 1
    assert report.contradictions[0].key == "status"
    assert not report.healthy


def test_lint_detects_stubs():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Tiny\nx")  # no claims, tiny body → stub
    report = wiki.lint()
    assert "tiny" in report.stubs


class _GhostLinkProvider:
    """Returns a page that links to a slug which is never created → dangling."""

    def generate(self, system: str, prompt: str) -> str:
        return (
            '{"pages": [{"slug": "alpha", "title": "Alpha", "action": "create", '
            '"body": "# Alpha\\nLinks to a page that does not exist.", '
            '"links": ["ghost"], "claims": {"k": "v"}, "contradictions": []}]}'
        )


def test_lint_detects_dangling_links_and_missing_concepts():
    wiki = KnowledgeWiki(cognition=LLMWikiCognition(provider=_GhostLinkProvider()))
    wiki.ingest("seed source — provider decides the page")
    report = wiki.lint()
    assert ("alpha", "ghost") in report.dangling_links
    assert "ghost" in report.missing_concepts
    assert not report.healthy


def test_lint_summary_reflects_state():
    wiki = KnowledgeWiki()
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits in the agent.\ncount: 8")
    assert "healthy" in wiki.lint().summary()
