"""
tests/test_wiki_answer_reuse.py

Phase 2 (slice D) — answer-reuse closes the compounding loop: promoted
``wiki:answer`` records re-enter retrieval, get reported in ``reused_answers``,
and are threaded into the next promotion's provenance. All offline; no API keys.
"""

from __future__ import annotations

from organic_agentic_autodev.knowledge_wiki import KnowledgeWiki


def _seed(wiki: KnowledgeWiki) -> None:
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits.\ntrait_count: 8")
    wiki.ingest("topic: Pathfinder\nNetworkX graph routing.\nconductance: 0.01-1.0")


def test_first_query_has_no_reused_answers():
    wiki = KnowledgeWiki()
    _seed(wiki)
    result = wiki.query("genome traits")
    assert result.reused_answers == []          # nothing promoted yet to reuse


def test_repeat_query_reuses_prior_answer():
    wiki = KnowledgeWiki()
    _seed(wiki)
    first = wiki.query("genome traits")
    second = wiki.query("genome traits")
    assert first.promoted_record_id is not None
    assert first.promoted_record_id in second.reused_answers


def test_reused_answer_is_threaded_into_new_promotion_provenance():
    wiki = KnowledgeWiki()
    _seed(wiki)
    first = wiki.query("genome traits")
    second = wiki.query("genome traits")
    # The second promoted answer traces back to the first (compounding graph).
    promoted = {
        r.record_id: r for r in wiki.mouseion.query_knowledge(KnowledgeWiki.ANSWER_TAG)
    }
    second_record = promoted[second.promoted_record_id]
    assert first.promoted_record_id in second_record.provenance_refs


def test_reuse_can_be_disabled():
    wiki = KnowledgeWiki()
    _seed(wiki)
    wiki.query("genome traits")
    result = wiki.query("genome traits", reuse_answers=False)
    assert result.reused_answers == []


def test_unrelated_repeat_does_not_reuse():
    wiki = KnowledgeWiki()
    _seed(wiki)
    wiki.query("genome traits")                 # promotes a genome answer
    result = wiki.query("pathfinder conductance")  # different topic
    assert result.reused_answers == []


def test_reuse_does_not_change_grounding_or_pages():
    wiki = KnowledgeWiki()
    _seed(wiki)
    wiki.query("genome traits")
    second = wiki.query("genome traits")
    # grounding stays strictly page-based (drives the slice-C grounding SLI).
    assert second.grounded
    assert second.pages == ["genome"]


def test_answer_reuse_is_deterministic():
    wiki = KnowledgeWiki()
    _seed(wiki)
    wiki.query("genome traits")
    a = wiki.query("genome traits", promote=False).reused_answers
    b = wiki.query("genome traits", promote=False).reused_answers
    assert a == b and a != []
