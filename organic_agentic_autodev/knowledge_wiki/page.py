"""
organic_agentic_autodev/knowledge_wiki/page.py

Data shapes for the compounding knowledge wiki (Phase 1).

These are *flesh*, not shell: they live inside the knowledge_wiki package and may
evolve freely. Durable persistence still goes through the stable
``KnowledgeRecordV0`` contract (see ``wiki.py``), so changing these classes never
breaks a downstream consumer.

A WikiPage is the LLM-owned middle layer of Karpathy's three-layer model
(immutable raw sources → LLM-owned wiki → human-curated schema). It is markdown
the system maintains, cross-references, and lints — not a verbatim copy of a
source.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from organic_agentic_autodev.utils.helpers import now_ms


def slugify(text: str) -> str:
    """Deterministic, dependency-free slug: lowercased, hyphenated, trimmed."""
    out: list[str] = []
    prev_dash = False
    for ch in text.strip().lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-") or "untitled"


@dataclass
class PageOp:
    """
    One proposed mutation to the wiki, emitted by a WikiCognition during ingest.

    The cognition layer (deterministic or LLM) decides *what* should change; the
    wiki applies it. ``action`` is "create" or "update". ``links`` are slugs this
    page references. ``claims`` are structured key→value facts used for
    contradiction detection. ``contradictions`` are (key, old, new) tuples the
    cognition already detected against the prior page state.
    """

    slug: str
    title: str
    action: str  # "create" | "update"
    body: str
    links: list[str] = field(default_factory=list)
    claims: dict[str, str] = field(default_factory=dict)
    contradictions: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class WikiPage:
    """A single LLM-maintained wiki page."""

    slug: str
    title: str
    body: str
    links: set[str] = field(default_factory=set)
    claims: dict[str, str] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    version: int = 1
    created_at_ms: int = field(default_factory=now_ms)
    updated_at_ms: int = field(default_factory=now_ms)


@dataclass
class Contradiction:
    """A conflict surfaced during ingest — flagged, never silently overwritten."""

    slug: str
    key: str
    existing: str
    incoming: str

    def describe(self) -> str:
        return (
            f"{self.slug}: claim '{self.key}' was '{self.existing}', "
            f"source asserts '{self.incoming}'"
        )


@dataclass
class IngestResult:
    """Outcome of one ingest call — what was created, updated, and conflicted."""

    source_record_id: str
    pages_created: list[str] = field(default_factory=list)
    pages_updated: list[str] = field(default_factory=list)
    links_added: list[tuple[str, str]] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.pages_created or self.pages_updated)


@dataclass
class QueryResult:
    """Outcome of one query — the answer, the pages it drew on, and whether the
    answer was promoted into the durable store (compounding knowledge)."""

    question: str
    answer: str
    pages: list[str] = field(default_factory=list)
    grounded: bool = False
    promoted_record_id: str | None = None


@dataclass
class LintReport:
    """Health check over the wiki layer — Karpathy's ``lint`` operation.

    Findings are structural and deterministic (no wall-clock): disconnected
    pages, links to non-existent pages, referenced-but-missing concepts,
    unresolved contradictions, and under-developed stubs.
    """

    page_count: int
    orphans: list[str] = field(default_factory=list)
    dangling_links: list[tuple[str, str]] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    stubs: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return not (
            self.orphans
            or self.dangling_links
            or self.missing_concepts
            or self.contradictions
            or self.stubs
        )

    def summary(self) -> str:
        if self.healthy:
            return f"wiki healthy — {self.page_count} page(s), no findings"
        return (
            f"wiki: {self.page_count} page(s) — "
            f"{len(self.orphans)} orphan, "
            f"{len(self.dangling_links)} dangling link, "
            f"{len(self.missing_concepts)} missing concept, "
            f"{len(self.contradictions)} contradiction, "
            f"{len(self.stubs)} stub"
        )
