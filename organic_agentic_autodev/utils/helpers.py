"""
src/utils/helpers.py

Shared utilities: structured logging, text sanitization, ID generation.
Prompt injection prevention is non-negotiable for all external input.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from typing import Any


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def new_id(prefix: str = "") -> str:
    """Return a short, unique, prefixed identifier."""
    short = uuid.uuid4().hex[:12]
    return f"{prefix}{short}" if prefix else short


def now_ms() -> int:
    """Current time as integer milliseconds since epoch."""
    return int(time.time() * 1000)


def content_hash(text: str) -> str:
    """Stable SHA-256 fingerprint for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Prompt injection prevention
# ---------------------------------------------------------------------------

# Patterns that indicate attempted prompt injection via external content
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)", re.IGNORECASE),
    re.compile(r"new\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[\/INST\]"),
    re.compile(r"###\s*(instruction|system|human|assistant)\s*:", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a\s+)", re.IGNORECASE),
    re.compile(r"disregard\s+(your|all|previous)", re.IGNORECASE),
]

_MAX_SAFE_LEN = 32_768  # characters; truncate beyond this


def sanitize_text(raw: str) -> str:
    """
    Sanitize external text before feeding it to an LLM or storing it in the
    Mouseion.  Removes injection patterns and truncates to a safe length.
    """
    if not isinstance(raw, str):
        raw = str(raw)

    # Hard truncation first — cheap fence before expensive regex
    text = raw[:_MAX_SAFE_LEN]

    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[REDACTED]", text)

    return text


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize all string values in a dict."""
    result: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = sanitize_text(v)
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [sanitize_text(i) if isinstance(i, str) else i for i in v]
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Structured logging (lightweight, no external dep)
# ---------------------------------------------------------------------------

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a consistently configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# ---------------------------------------------------------------------------
# Clamp / normalise helpers
# ---------------------------------------------------------------------------

def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def normalise(values: list[float]) -> list[float]:
    """Min-max normalise a list of floats to [0, 1]."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]
