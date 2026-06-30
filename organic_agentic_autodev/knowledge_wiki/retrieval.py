"""
organic_agentic_autodev/knowledge_wiki/retrieval.py

Relevance scoring + pluggable retrieval strategies for wiki ``query``.

The scoring primitives (``tokenize``, ``relevance``) are pure functions — no
wall-clock, no RNG — so ranking is fully reproducible and testable in isolation.

Retrieval is a **strategy** (Phase 2, slice A): ``KnowledgeWiki`` ranks pages
through a ``Retriever``, so how relevance is computed is swappable without
touching the orchestrator (MoltBook flesh).

  - ``LexicalRetriever`` (default) — weighted token overlap; the Phase 1
    behavior, unchanged. Fully offline and deterministic.
  - ``VectorRetriever`` — cosine similarity over an ``Embedder``. Defaults to the
    deterministic, offline ``HashingEmbedder`` (so tests stay reproducible);
    inject ``SentenceTransformerEmbedder`` for real semantic retrieval. FAISS /
    Qdrant are a *scale* swap behind the embedder's ``VectorStore`` — deferred
    until a measured corpus size needs them (no premature optimization).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from organic_agentic_autodev.knowledge_wiki.page import WikiPage
from organic_agentic_autodev.mouseion.backends.vector_store import (
    Embedder,
    HashingEmbedder,
)

# Small, fixed stop list — kept tiny on purpose (no external corpus dependency).
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
        "has", "had", "was", "were", "its", "his", "her", "their", "with",
        "what", "when", "where", "which", "who", "whom", "how", "why", "does",
        "did", "this", "that", "these", "those", "into", "from", "than", "then",
        "they", "them", "your", "ours", "about", "over", "under", "have",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercase alnum tokens, dropping stopwords and tokens shorter than 3."""
    tokens: list[str] = []
    word: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            word.append(ch)
        elif word:
            tokens.append("".join(word))
            word = []
    if word:
        tokens.append("".join(word))
    return [t for t in tokens if len(t) >= 3 and t not in _STOPWORDS]


def relevance(question: str, page: WikiPage) -> float:
    """
    Score a page against a question by weighted token overlap.

    Title matches count most (3×), structured claims next (2×), body least (1×),
    normalised by the number of question tokens so scores are comparable across
    questions. Returns 0.0 when there is no overlap.
    """
    q = set(tokenize(question))
    if not q:
        return 0.0
    title = set(tokenize(page.title))
    claims = set(tokenize(" ".join([*page.claims.keys(), *page.claims.values()])))
    body = set(tokenize(page.body))
    score = 3 * len(q & title) + 2 * len(q & claims) + 1 * len(q & body)
    return score / len(q)


# ---------------------------------------------------------------------------
# Retrieval strategies (the swappable seam)
# ---------------------------------------------------------------------------

class Retriever(ABC):
    """Ranks wiki pages against a question, returning only grounded hits.

    ``rank`` returns at most ``k`` pages, most-relevant first, already filtered to
    those that actually match (so ``query`` can treat a non-empty result as
    "grounded"). Ties break on slug for determinism.
    """

    name: str = "abstract"

    @abstractmethod
    def rank(self, question: str, pages: list[WikiPage], *, k: int) -> list[WikiPage]:
        raise NotImplementedError


class LexicalRetriever(Retriever):
    """Weighted token-overlap ranking — the Phase 1 default, unchanged.

    A page is grounded when its ``relevance`` score is > 0 (some token overlap).
    """

    name = "lexical"

    def rank(self, question: str, pages: list[WikiPage], *, k: int) -> list[WikiPage]:
        scored = sorted(
            ((relevance(question, p), p) for p in pages),
            key=lambda pair: (-pair[0], pair[1].slug),
        )
        return [page for score, page in scored if score > 0][:k]


class VectorRetriever(Retriever):
    """Cosine-similarity ranking over an ``Embedder``.

    Defaults to the offline, deterministic ``HashingEmbedder``. Page text is
    weighted to echo the lexical weighting (title 3×, claims 2×, body 1×) before
    embedding. ``min_similarity`` is the grounding threshold: cosine below it is
    treated as noise (no match), so unrelated questions stay ungrounded rather
    than grounding on hash-collision drift.

    The default ``0.3`` is **embedder-dependent and deliberately conservative**.
    ``HashingEmbedder`` is a bag-of-words proxy whose feature-hash collisions can
    push a *disjoint* short query to ~0.25 cosine — rivaling a genuine weak match.
    A high threshold favors precision (never promote a noise-grounded answer into
    the durable store) over recall. A real semantic embedder
    (``SentenceTransformerEmbedder``) separates signal from noise far better and
    warrants a *lower* threshold. See ``docs/discovery-log.md`` (2026-06-30).
    """

    name = "vector"

    def __init__(
        self, embedder: Embedder | None = None, *, min_similarity: float = 0.3
    ) -> None:
        self._embedder: Embedder = embedder or HashingEmbedder()
        self._min = min_similarity

    @staticmethod
    def _page_text(page: WikiPage) -> str:
        claims = " ".join([*page.claims.keys(), *page.claims.values()])
        # Repetition is the weighting: title 3×, claims 2×, body 1×.
        return " ".join(
            [page.title, page.title, page.title, claims, claims, page.body]
        )

    def rank(self, question: str, pages: list[WikiPage], *, k: int) -> list[WikiPage]:
        if not pages:
            return []
        q = self._embedder.embed(question)
        scored = [
            (float(self._embedder.embed(self._page_text(p)) @ q), p) for p in pages
        ]
        scored.sort(key=lambda pair: (-pair[0], pair[1].slug))
        return [page for sim, page in scored if sim >= self._min][:k]
