"""
examples/knowledge_wiki_demo.py

Compounding Knowledge Wiki (Phase 1) — ingest demonstration.

Shows the three behaviours of the ``ingest`` operation, fully offline (the
deterministic cognition; no API key required):
  1. A raw source becomes an LLM-owned wiki page (sources stay immutable).
  2. A second source on the same topic *updates* the page (no duplicate) and
     accumulates provenance.
  3. Cross-references link related pages; contradictions are surfaced, not
     silently overwritten.

Run:
    python examples/knowledge_wiki_demo.py
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.WARNING)

from organic_agentic_autodev.knowledge_wiki import KnowledgeWiki  # noqa: E402


def main() -> None:
    print("=" * 70)
    print("  📚  Compounding Knowledge Wiki — ingest demo")
    print("=" * 70)

    wiki = KnowledgeWiki()

    # 1. First source → a new page.
    wiki.ingest("topic: Genome\nEncodes eight behavioural traits in [0, 1].")

    # 2. A second source that references Genome → a new page that links to it.
    wiki.ingest(
        "topic: Stem Cell\n"
        "A blank-slate agent. It reads its Genome to decide whether to differentiate.\n"
        "drives: seek, scan, evaluate, differentiate"
    )

    # 3. Update an existing page, and introduce a contradiction.
    wiki.ingest("topic: Stem Cell\nstatus: totipotent")
    result = wiki.ingest("topic: Stem Cell\nstatus: differentiated")

    print(f"\nPages in wiki: {wiki.page_count()}")
    for page in wiki.pages():
        links = ", ".join(sorted(page.links)) or "—"
        print(f"\n• {page.title}  (slug={page.slug}, v{page.version})")
        print(f"    links → {links}")
        print(f"    claims  {page.claims}")
        print(f"    sources {len(page.source_refs)}")

    if result.contradictions:
        print("\n⚠️  Contradictions surfaced (existing value kept pending review):")
        for c in wiki.contradictions():
            print(f"    - {c.describe()}")

    # The Mouseion now holds both immutable sources and page snapshots.
    sources = wiki.mouseion.query_knowledge(KnowledgeWiki.SOURCE_TAG)
    snapshots = wiki.mouseion.query_knowledge(KnowledgeWiki.PAGE_TAG)
    print(f"\nMouseion: {len(sources)} immutable sources, {len(snapshots)} page snapshots")
    print("=" * 70)


if __name__ == "__main__":
    main()
