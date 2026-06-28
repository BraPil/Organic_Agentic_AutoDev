"""
src/mouseion/backends — swappable storage flesh for the Mouseion.

Public API:
  KnowledgeBackend  — abstract storage contract (shell)
  MemoryBackend     — in-memory default (flesh)
  SQLiteBackend     — durable SQLite store (flesh)
  VectorStore       — semantic similarity search (additive)
  HashingEmbedder / SentenceTransformerEmbedder — embedders for VectorStore
"""

from __future__ import annotations

from organic_agentic_autodev.mouseion.backends.base import KnowledgeBackend
from organic_agentic_autodev.mouseion.backends.memory_backend import MemoryBackend
from organic_agentic_autodev.mouseion.backends.sqlite_backend import SQLiteBackend
from organic_agentic_autodev.mouseion.backends.vector_store import (
    Embedder,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    VectorStore,
)

__all__ = [
    "KnowledgeBackend",
    "MemoryBackend",
    "SQLiteBackend",
    "VectorStore",
    "Embedder",
    "HashingEmbedder",
    "SentenceTransformerEmbedder",
]
