"""
organic_agentic_autodev/knowledge_wiki/cognition.py

The synthesis brain for the knowledge wiki.

A ``WikiCognition`` decides *what* should change in the wiki when a new source
arrives — which page to create or update, how to phrase it, what it links to,
and whether the source contradicts what is already written. The wiki itself
(``wiki.py``) only *applies* these decisions; it never reasons.

Two implementations, mirroring the rest of the codebase's cognition pattern
(abstract interface + deterministic offline impl + live LLM impl):

  - ``DeterministicWikiCognition`` — no network, fully reproducible. The default.
    Tests run entirely against this, so CI stays green with no API key.
  - ``LLMWikiCognition`` — wraps a bridge ``CognitionProvider`` (Anthropic when a
    key is present). Falls back to the deterministic path on any parse/transport
    failure, so ingest never crashes because a model call misbehaved.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from organic_agentic_autodev.cognition.bridge import CognitionProvider, make_cognition
from organic_agentic_autodev.knowledge_wiki.page import PageOp, WikiPage, slugify
from organic_agentic_autodev.utils.helpers import get_logger, sanitize_text

logger = get_logger("knowledge_wiki.cognition")

_RESERVED_CLAIM_KEYS = {"title", "topic"}


# ---------------------------------------------------------------------------
# Shared source parsing (deterministic; used by both impls)
# ---------------------------------------------------------------------------

def _parse_source(text: str) -> tuple[dict[str, str], list[str]]:
    """
    Split a source into structured ``claims`` (``Key: Value`` lines) and free
    ``prose`` lines. A line is a claim only if it has a short, punctuation-free
    key before the first colon — otherwise it is prose (e.g. a sentence with a
    colon in it).
    """
    claims: dict[str, str] = {}
    prose: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            is_claim = (
                bool(key)
                and bool(value)
                and len(key.split()) <= 4
                and not key.endswith((".", "!", "?"))
            )
            if is_claim:
                claims[key.lower()] = value
                continue
        prose.append(line)
    return claims, prose


def _first_words(prose: list[str], claims: dict[str, str], n: int = 8) -> str:
    """Pick a deterministic page title when none was supplied."""
    if prose:
        return " ".join(prose[0].split()[:n])
    for key, value in claims.items():
        if key not in _RESERVED_CLAIM_KEYS:
            return value[:60]
    return "untitled"


def _detect_links(text: str, existing: dict[str, WikiPage], exclude: str) -> list[str]:
    """Cross-reference: existing pages whose title or slug appears in the source."""
    hay = text.lower()
    found = {
        slug
        for slug, page in existing.items()
        if slug != exclude and (page.title.lower() in hay or slug in hay)
    }
    return sorted(found)


def _render_body(title: str, prose: list[str], claims: dict[str, str]) -> str:
    """Render a deterministic markdown page body from prose + structured facts."""
    parts = [f"# {title}", ""]
    if prose:
        parts.append("\n".join(prose))
        parts.append("")
    facts = {k: v for k, v in claims.items() if k not in _RESERVED_CLAIM_KEYS}
    if facts:
        parts.append("## Facts")
        parts.extend(f"- **{k}**: {v}" for k, v in sorted(facts.items()))
    return "\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class WikiCognition(ABC):
    """Decides the wiki mutations a new source implies."""

    name: str = "abstract"

    @abstractmethod
    def synthesize(
        self,
        *,
        source_text: str,
        source_id: str,
        topic: str | None,
        existing_pages: dict[str, WikiPage],
    ) -> list[PageOp]:
        """Return the page operations a source implies (create/update + links)."""
        raise NotImplementedError

    @abstractmethod
    def answer(self, *, question: str, pages: list[WikiPage]) -> str:
        """Compose an answer to a question from the retrieved wiki pages."""
        raise NotImplementedError


def _compose_answer(question: str, pages: list[WikiPage]) -> str:
    """Deterministic answer composition shared by both cognition impls."""
    if not pages:
        return "No relevant wiki pages were found for this question."
    lines = [f"Based on {len(pages)} wiki page(s):"]
    for page in pages:
        facts = (
            "; ".join(f"{k}={v}" for k, v in sorted(page.claims.items()))
            or "(no structured facts)"
        )
        lines.append(f"- {page.title}: {facts}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deterministic (default, offline)
# ---------------------------------------------------------------------------

class DeterministicWikiCognition(WikiCognition):
    """Reproducible, dependency-free synthesis — the offline default."""

    name = "deterministic"

    def synthesize(
        self,
        *,
        source_text: str,
        source_id: str,
        topic: str | None,
        existing_pages: dict[str, WikiPage],
    ) -> list[PageOp]:
        claims, prose = _parse_source(source_text)
        title = (
            topic
            or claims.get("title")
            or claims.get("topic")
            or _first_words(prose, claims)
        )
        slug = slugify(title)
        existing = existing_pages.get(slug)

        merged: dict[str, str] = dict(existing.claims) if existing else {}
        contradictions: list[tuple[str, str, str]] = []
        for key, value in claims.items():
            if key in _RESERVED_CLAIM_KEYS:
                continue
            if key in merged and merged[key] != value:
                # Conflict: keep the existing claim, surface the contradiction.
                contradictions.append((key, merged[key], value))
            else:
                merged[key] = value

        links = _detect_links(source_text, existing_pages, exclude=slug)
        body = _render_body(title, prose, merged)
        action = "update" if existing else "create"
        return [
            PageOp(
                slug=slug,
                title=title,
                action=action,
                body=body,
                links=links,
                claims=merged,
                contradictions=contradictions,
            )
        ]

    def answer(self, *, question: str, pages: list[WikiPage]) -> str:
        return _compose_answer(question, pages)


# ---------------------------------------------------------------------------
# LLM-backed (live; degrades to deterministic on any failure)
# ---------------------------------------------------------------------------

class LLMWikiCognition(WikiCognition):
    """
    Synthesis backed by a bridge ``CognitionProvider`` (Anthropic when keyed).

    The model is asked for a strict JSON op list. Any failure — transport error,
    unparseable output, empty result — falls back to the deterministic path, so
    ingest is never blocked by model behaviour.
    """

    name = "llm"

    def __init__(self, provider: CognitionProvider | None = None) -> None:
        self._provider = provider or make_cognition()
        self._fallback = DeterministicWikiCognition()

    def synthesize(
        self,
        *,
        source_text: str,
        source_id: str,
        topic: str | None,
        existing_pages: dict[str, WikiPage],
    ) -> list[PageOp]:
        try:
            system, prompt = self._build_prompt(source_text, topic, existing_pages)
            ops = self._parse_ops(self._provider.generate(system, prompt), existing_pages)
            if ops:
                return ops
            logger.info("LLM wiki synthesis returned no ops; using deterministic fallback")
        except Exception as exc:  # noqa: BLE001 — provider must never break ingest
            logger.warning("LLM wiki synthesis failed (%s); deterministic fallback", exc)
        return self._fallback.synthesize(
            source_text=source_text,
            source_id=source_id,
            topic=topic,
            existing_pages=existing_pages,
        )

    def answer(self, *, question: str, pages: list[WikiPage]) -> str:
        if not pages:
            return _compose_answer(question, pages)
        try:
            context = "\n\n".join(f"## {p.title}\n{p.body}" for p in pages)
            system = (
                "Answer the question using ONLY the provided wiki pages. Be concise "
                "and concrete. If the pages do not answer it, say so plainly."
            )
            prompt = f"QUESTION:\n{question}\n\nWIKI PAGES:\n{context}\n\nAnswer:"
            text = sanitize_text(self._provider.generate(system, prompt)).strip()
            if text:
                return text
        except Exception as exc:  # noqa: BLE001 — provider must never break query
            logger.warning("LLM answer failed (%s); deterministic fallback", exc)
        return _compose_answer(question, pages)

    # -- prompt + parse -----------------------------------------------------

    @staticmethod
    def _build_prompt(
        source_text: str, topic: str | None, existing_pages: dict[str, WikiPage]
    ) -> tuple[str, str]:
        index = (
            "\n".join(f"- {p.slug}: {p.title}" for p in existing_pages.values())
            or "(the wiki is empty)"
        )
        system = (
            "You maintain a compounding markdown knowledge wiki. Given a new source "
            "and the current page index, decide which pages to create or update. "
            "Cross-reference related pages via their slugs. If the source contradicts "
            "an existing page, record the contradiction rather than silently "
            "overwriting. Return ONLY JSON of the form: "
            '{"pages":[{"slug","title","action":"create|update","body",'
            '"links":[slug],"claims":{key:value},'
            '"contradictions":[{"key","existing","incoming"}]}]}'
        )
        hint = f"\nSUGGESTED TOPIC: {topic}" if topic else ""
        prompt = (
            f"CURRENT PAGE INDEX:\n{index}\n\nNEW SOURCE:\n{source_text}{hint}\n\n"
            "Return only the JSON object."
        )
        return system, prompt

    @staticmethod
    def _parse_ops(text: str, existing_pages: dict[str, WikiPage]) -> list[PageOp]:
        data = _extract_json(text)
        raw_pages = data.get("pages") if isinstance(data, dict) else None
        if not isinstance(raw_pages, list):
            return []
        ops: list[PageOp] = []
        for entry in raw_pages:
            if not isinstance(entry, dict):
                continue
            title = sanitize_text(str(entry.get("title", "")).strip())
            if not title:
                continue
            slug = slugify(str(entry.get("slug") or title))
            action = "update" if slug in existing_pages else "create"
            if str(entry.get("action", "")).lower() in {"create", "update"}:
                action = str(entry["action"]).lower()
            claims = {
                str(k).lower(): sanitize_text(str(v))
                for k, v in (entry.get("claims") or {}).items()
                if str(k).lower() not in _RESERVED_CLAIM_KEYS
            }
            contradictions = [
                (
                    str(c.get("key", "")).lower(),
                    sanitize_text(str(c.get("existing", ""))),
                    sanitize_text(str(c.get("incoming", ""))),
                )
                for c in (entry.get("contradictions") or [])
                if isinstance(c, dict) and c.get("key")
            ]
            links = sorted(
                {slugify(str(s)) for s in (entry.get("links") or []) if str(s).strip()}
            )
            body = sanitize_text(str(entry.get("body", ""))).strip() + "\n"
            ops.append(
                PageOp(
                    slug=slug,
                    title=title,
                    action=action,
                    body=body,
                    links=links,
                    claims=claims,
                    contradictions=contradictions,
                )
            )
        return ops


def _extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model response (handles ```fences```)."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, IndexError):
        return {}
