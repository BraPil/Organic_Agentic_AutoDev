"""
organic_agentic_autodev/knowledge_wiki/wiki.py

The compounding knowledge wiki — Phase 1, ``ingest`` operation.

Karpathy's three layers, realised on the Mouseion:
  - **Raw sources** (immutable ground truth) — stored as ``KnowledgeRecordV0``
    tagged ``wiki:source``. Never mutated.
  - **Wiki** (LLM-owned markdown) — ``WikiPage`` objects, with each version
    snapshotted to a ``KnowledgeRecordV0`` tagged ``wiki:page`` carrying
    provenance back to the sources that shaped it.
  - **Schema** (human-curated config) — ``docs/knowledge.md`` + CLAUDE.md.

``ingest(source)`` stores the source immutably, asks the ``WikiCognition`` what
pages the source implies, then applies those operations: creating/updating pages,
recording cross-references, and surfacing contradictions instead of silently
overwriting. Synthesis lives entirely in the cognition layer; this class only
applies decisions and persists them — keeping the orchestrator thin (it moves
data, it doesn't transform it).

``query`` and ``lint`` arrive in Phase 1's P1.3.
"""

from __future__ import annotations

from collections import defaultdict

from organic_agentic_autodev.knowledge_wiki.cognition import (
    DeterministicWikiCognition,
    WikiCognition,
)
from organic_agentic_autodev.knowledge_wiki.page import (
    Contradiction,
    IngestResult,
    LintReport,
    PageOp,
    QueryResult,
    WikiPage,
)
from organic_agentic_autodev.knowledge_wiki.retrieval import (
    LexicalRetriever,
    Retriever,
)
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.utils.helpers import get_logger, now_ms, sanitize_text

logger = get_logger("knowledge_wiki.wiki")


class KnowledgeWiki:
    """An LLM-maintained, compounding wiki layered over a Mouseion."""

    SOURCE_TAG = "wiki:source"
    PAGE_TAG = "wiki:page"
    ANSWER_TAG = "wiki:answer"

    #: A page is a "stub" (lint finding) if it carries no structured claims and
    #: its rendered body is shorter than this many characters.
    STUB_MAX_LEN = 80

    #: Raw sources are stored at full fidelity — this is the *capture* confidence
    #: (a faithful copy of what was supplied), not a claim of truth.
    SOURCE_CONFIDENCE = 1.0
    #: Wiki pages are syntheses, not adversarially scored findings. Adversarial
    #: scoring is the cognition bridge's job; lint/query (P1.3) refine pages.
    PAGE_CONFIDENCE = 0.5

    def __init__(
        self,
        mouseion: Mouseion | None = None,
        cognition: WikiCognition | None = None,
        retriever: Retriever | None = None,
    ) -> None:
        self._mouseion = mouseion or Mouseion()
        self._cog = cognition or DeterministicWikiCognition()
        self._retriever = retriever or LexicalRetriever()
        self._pages: dict[str, WikiPage] = {}
        self._contradictions: list[Contradiction] = []
        logger.info(
            "KnowledgeWiki ready (cognition=%s, retriever=%s)",
            self._cog.name, self._retriever.name,
        )

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    @property
    def mouseion(self) -> Mouseion:
        return self._mouseion

    def page(self, slug: str) -> WikiPage | None:
        return self._pages.get(slug)

    def pages(self) -> list[WikiPage]:
        return list(self._pages.values())

    def page_count(self) -> int:
        return len(self._pages)

    def contradictions(self) -> list[Contradiction]:
        """All contradictions surfaced so far (for review / future lint)."""
        return list(self._contradictions)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest(
        self,
        source_text: str,
        *,
        source_id: str | None = None,
        topic: str | None = None,
        source_tags: list[str] | None = None,
    ) -> IngestResult:
        """
        Ingest one raw source: store it immutably, synthesise the wiki pages it
        implies, and apply them. Returns what changed.
        """
        safe = sanitize_text(source_text)
        if not safe.strip():
            raise ValueError("cannot ingest an empty source")

        # 1. Store the raw source as immutable ground truth.
        source = self._mouseion.store_knowledge(
            author_id=source_id or "wiki:ingest",
            content=safe,
            topic_tags=[self.SOURCE_TAG, *(source_tags or [])],
            confidence=self.SOURCE_CONFIDENCE,
        )
        result = IngestResult(source_record_id=source.record_id)

        # 2. Decide what changes (synthesis is the cognition layer's job).
        ops = self._cog.synthesize(
            source_text=safe,
            source_id=source.record_id,
            topic=topic,
            existing_pages=self._pages,
        )

        # 3. Apply each operation.
        for op in ops:
            self._apply(op, source.record_id, result)

        logger.info(
            "ingest %s → +%d pages, ~%d updated, %d link(s), %d contradiction(s)",
            source.record_id,
            len(result.pages_created),
            len(result.pages_updated),
            len(result.links_added),
            len(result.contradictions),
        )
        return result

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self, question: str, *, k: int = 3, promote: bool = True
    ) -> QueryResult:
        """
        Answer a question from the wiki. Relevant pages are retrieved and
        composed into an answer; a grounded answer is *promoted* into the durable
        store (tagged ``wiki:answer``, with provenance to the sources it drew on)
        so valuable answers compound instead of vanishing.
        """
        safe_q = sanitize_text(question)
        if not safe_q.strip():
            raise ValueError("cannot query with an empty question")

        # Ranking is delegated to the retrieval strategy (lexical by default,
        # vector when injected); it returns only grounded hits, most-relevant first.
        hits = self._retriever.rank(safe_q, list(self._pages.values()), k=k)
        answer = self._cog.answer(question=safe_q, pages=hits)
        grounded = bool(hits)

        promoted_id: str | None = None
        if promote and grounded:
            provenance: list[str] = []
            for page in hits:
                for ref in page.source_refs:
                    if ref not in provenance:
                        provenance.append(ref)
            record = self._mouseion.store_knowledge(
                author_id=self.ANSWER_TAG,
                content=answer,
                topic_tags=[self.ANSWER_TAG],
                confidence=self.PAGE_CONFIDENCE,
                provenance_refs=provenance,
            )
            promoted_id = record.record_id

        logger.info(
            "query %r → %d page(s), grounded=%s, promoted=%s",
            safe_q[:60], len(hits), grounded, bool(promoted_id),
        )
        return QueryResult(
            question=safe_q,
            answer=answer,
            pages=[p.slug for p in hits],
            grounded=grounded,
            promoted_record_id=promoted_id,
        )

    # ------------------------------------------------------------------
    # Lint
    # ------------------------------------------------------------------

    def lint(self) -> LintReport:
        """
        Structural health check over the wiki layer. Detects disconnected pages
        (orphans), links to non-existent pages (dangling), referenced-but-missing
        concepts, unresolved contradictions, and under-developed stubs.

        Deterministic by design — no wall-clock staleness (that needs a tick/
        version baseline; deferred to keep lint reproducible).
        """
        slugs = set(self._pages)
        inbound: dict[str, set[str]] = defaultdict(set)
        outbound: dict[str, set[str]] = defaultdict(set)
        dangling: list[tuple[str, str]] = []

        for slug, page in self._pages.items():
            for link in sorted(page.links):
                outbound[slug].add(link)
                if link in slugs:
                    inbound[link].add(slug)
                else:
                    dangling.append((slug, link))

        # A lone page is the whole wiki, not an orphan — only flag when >1 page.
        orphans = (
            sorted(s for s in slugs if not inbound[s] and not outbound[s])
            if len(slugs) > 1
            else []
        )
        missing = sorted({target for _, target in dangling})
        stubs = sorted(
            slug
            for slug, page in self._pages.items()
            if not page.claims and len(page.body) < self.STUB_MAX_LEN
        )

        report = LintReport(
            page_count=len(self._pages),
            orphans=orphans,
            dangling_links=sorted(dangling),
            missing_concepts=missing,
            contradictions=self.contradictions(),
            stubs=stubs,
        )
        logger.info("lint → %s", report.summary())
        return report

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _apply(self, op: PageOp, source_ref: str, result: IngestResult) -> None:
        page = self._pages.get(op.slug)
        if page is None:
            page = WikiPage(slug=op.slug, title=op.title, body=op.body)
            self._pages[op.slug] = page
            result.pages_created.append(op.slug)
        else:
            page.title = op.title or page.title
            page.body = op.body
            page.version += 1
            page.updated_at_ms = now_ms()
            result.pages_updated.append(op.slug)

        page.claims = dict(op.claims)

        for link in op.links:
            if link != op.slug and link not in page.links:
                page.links.add(link)
                result.links_added.append((op.slug, link))

        if source_ref not in page.source_refs:
            page.source_refs.append(source_ref)

        for key, existing, incoming in op.contradictions:
            conflict = Contradiction(
                slug=op.slug, key=key, existing=existing, incoming=incoming
            )
            self._contradictions.append(conflict)
            result.contradictions.append(conflict)
            logger.warning("contradiction — %s", conflict.describe())

        # Snapshot this page version durably, with provenance to its sources.
        self._mouseion.store_knowledge(
            author_id=self.PAGE_TAG,
            content=page.body,
            topic_tags=[self.PAGE_TAG, page.slug],
            confidence=self.PAGE_CONFIDENCE,
            provenance_refs=list(page.source_refs),
        )
