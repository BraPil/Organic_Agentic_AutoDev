"""
organic_agentic_autodev/knowledge_wiki/retrieval.py

Deterministic, dependency-free relevance scoring for wiki ``query``.

Pure functions, no wall-clock and no RNG, so ranking is fully reproducible and
testable in isolation. Semantic (vector) retrieval is a Phase 2 upgrade that can
slot in behind the same ``relevance`` signature; lexical overlap is enough to
ground answers offline today.
"""

from __future__ import annotations

from organic_agentic_autodev.knowledge_wiki.page import WikiPage

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
