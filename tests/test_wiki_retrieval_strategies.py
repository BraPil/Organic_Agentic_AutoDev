"""
tests/test_wiki_retrieval_strategies.py

Phase 2 (slice A) — pluggable wiki retrieval. Lexical stays the default (Phase 1
behavior unchanged); VectorRetriever adds cosine retrieval over the existing
offline, deterministic HashingEmbedder. All offline; no API keys, no new deps.
"""

from __future__ import annotations

from organic_agentic_autodev.knowledge_wiki import (
    KnowledgeWiki,
    LexicalRetriever,
    VectorRetriever,
)
from organic_agentic_autodev.observability import WikiHealthMonitor


def _seed(wiki: KnowledgeWiki) -> None:
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits.\ntrait_count: 8")
    wiki.ingest("topic: Pathfinder\nNetworkX graph routing.\nconductance: 0.01-1.0")


# ---------------------------------------------------------------------------
# Default strategy — Phase 1 behavior must not change
# ---------------------------------------------------------------------------

def test_default_retriever_is_lexical():
    assert KnowledgeWiki()._retriever.name == "lexical"


def test_lexical_default_still_ranks_and_grounds():
    wiki = KnowledgeWiki()  # default lexical
    _seed(wiki)
    result = wiki.query("how many traits does the genome encode?")
    assert result.grounded
    assert result.pages[0] == "genome"


# ---------------------------------------------------------------------------
# VectorRetriever
# ---------------------------------------------------------------------------

def test_vector_retriever_ranks_relevant_page_first():
    wiki = KnowledgeWiki(retriever=VectorRetriever())
    _seed(wiki)
    result = wiki.query("genome behavioural traits")
    assert result.grounded
    assert result.pages[0] == "genome"


def test_vector_retriever_stays_ungrounded_on_unrelated_query():
    wiki = KnowledgeWiki(retriever=VectorRetriever())
    _seed(wiki)
    # Disjoint vocabulary → cosine below the grounding threshold → no match.
    result = wiki.query("xylophone quasar marimba")
    assert not result.grounded
    assert result.pages == []
    assert result.promoted_record_id is None


def test_vector_retriever_promotes_grounded_answer():
    wiki = KnowledgeWiki(retriever=VectorRetriever())
    _seed(wiki)
    result = wiki.query("genome traits")
    # Compounding still works regardless of retrieval strategy.
    assert result.promoted_record_id is not None
    assert wiki.mouseion.query_knowledge(KnowledgeWiki.ANSWER_TAG)


def test_vector_retriever_respects_k_limit():
    wiki = KnowledgeWiki(retriever=VectorRetriever())
    wiki.ingest("topic: Alpha\nshared term cell membrane.")
    wiki.ingest("topic: Beta\nshared term cell membrane.")
    wiki.ingest("topic: Gamma\nshared term cell membrane.")
    result = wiki.query("cell membrane", k=2)
    assert len(result.pages) == 2


def test_vector_retrieval_is_deterministic():
    wiki = KnowledgeWiki(retriever=VectorRetriever())
    _seed(wiki)
    first = wiki.query("genome traits", promote=False).pages
    second = wiki.query("genome traits", promote=False).pages
    assert first == second


def test_min_similarity_threshold_gates_grounding():
    # A high threshold makes even an overlapping query ungrounded.
    strict = KnowledgeWiki(retriever=VectorRetriever(min_similarity=0.99))
    _seed(strict)
    assert not strict.query("genome traits").grounded


# ---------------------------------------------------------------------------
# Strategy interop with the slice-C health monitor
# ---------------------------------------------------------------------------

def test_grounding_sli_reflects_injected_vector_retriever():
    wiki = KnowledgeWiki(retriever=VectorRetriever())
    _seed(wiki)
    monitor = WikiHealthMonitor(
        wiki, probe_questions=["genome traits", "xylophone quasar marimba"]
    )
    grounding = monitor.evaluate()["evaluations"]["query_grounding_rate"]
    # One probe grounds, one does not → 0.5, measured through the vector retriever.
    assert grounding.sli_measurement.value == 0.5


def test_lexical_retriever_is_explicitly_injectable():
    wiki = KnowledgeWiki(retriever=LexicalRetriever())
    _seed(wiki)
    assert wiki.query("genome traits").pages[0] == "genome"
