"""
organic_agentic_autodev.knowledge_wiki

Phase 1 — the compounding knowledge wiki (Karpathy's ingest/query/lint pattern),
layered over the Mouseion. This package is additive *flesh*: it depends on the
stable Mouseion / cognition seams and changes no shell contracts.

Implemented: ``ingest`` (P1.2), ``query`` + ``lint`` (P1.3).

See ``docs/knowledge.md`` (schema) and ``adr/ADR-0001-compounding-knowledge-wiki.md``.
"""

from organic_agentic_autodev.knowledge_wiki.cognition import (
    DeterministicWikiCognition,
    LLMWikiCognition,
    WikiCognition,
)
from organic_agentic_autodev.knowledge_wiki.page import (
    Contradiction,
    IngestResult,
    LintReport,
    PageOp,
    QueryResult,
    WikiPage,
    slugify,
)
from organic_agentic_autodev.knowledge_wiki.retrieval import (
    LexicalRetriever,
    Retriever,
    VectorRetriever,
    relevance,
    tokenize,
)
from organic_agentic_autodev.knowledge_wiki.wiki import KnowledgeWiki

__all__ = [
    "KnowledgeWiki",
    "WikiCognition",
    "DeterministicWikiCognition",
    "LLMWikiCognition",
    "WikiPage",
    "PageOp",
    "IngestResult",
    "QueryResult",
    "LintReport",
    "Contradiction",
    "slugify",
    "tokenize",
    "relevance",
    "Retriever",
    "LexicalRetriever",
    "VectorRetriever",
]
