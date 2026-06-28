"""
src/mouseion/backends/vector_store.py

Semantic vector search over the knowledge corpus.

Enables ``mouseion.semantic_query(text, k=5)`` — retrieving records by meaning,
not just exact tag match. This is additive: it never changes existing APIs.

Design (offline-first, with an upgrade seam):
  - ``Embedder`` is a tiny protocol: text → unit vector (numpy array).
  - ``HashingEmbedder`` (default) is a dependency-free, deterministic bag-of-
    words feature-hashing embedder. It runs offline with zero configuration and
    gives meaningful cosine similarity for keyword/topic overlap — enough to
    demonstrate and test semantic retrieval reproducibly.
  - ``SentenceTransformerEmbedder`` is an optional upgrade: if
    ``sentence-transformers`` is installed, it produces real semantic
    embeddings. Swapping it in changes nothing else (MoltBook flesh).
  - The index is brute-force cosine over numpy. For the POC corpus size this is
    correct and fast; FAISS/Qdrant can replace ``_VectorIndex`` later behind the
    same interface for scale.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import numpy as np

from src.mouseion.contracts import KnowledgeRecordV0
from src.utils.helpers import get_logger

logger = get_logger("mouseion.vector_store")

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Embedder(Protocol):
    """Maps text to a fixed-dimension unit vector."""

    dim: int

    def embed(self, text: str) -> np.ndarray: ...


class HashingEmbedder:
    """
    Deterministic, dependency-free feature-hashing embedder.

    Each token is hashed into one of ``dim`` buckets (sign from a second hash to
    reduce collisions), the vector is L2-normalised. Cosine similarity between
    two such vectors reflects shared-vocabulary overlap — a serviceable,
    fully-offline proxy for semantic similarity.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    @staticmethod
    def _stable_hash(token: str) -> int:
        # blake2b → process-independent, deterministic across runs (unlike the
        # salted built-in hash()), so embeddings are fully reproducible.
        return int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big"
        )

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for tok in _tokenize(text):
            h = self._stable_hash(tok)
            bucket = h % self.dim
            sign = 1.0 if (h >> 1) % 2 == 0 else -1.0
            vec[bucket] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec


class SentenceTransformerEmbedder:  # pragma: no cover - optional dependency
    """Optional real-embedding upgrade (requires ``sentence-transformers``)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, text: str) -> np.ndarray:
        vec = self._model.encode([text], normalize_embeddings=True)[0]
        return np.asarray(vec, dtype=np.float32)


class VectorStore:
    """
    Brute-force cosine-similarity index over knowledge records.

    Parameters
    ----------
    embedder:
        Any object implementing the ``Embedder`` protocol. Defaults to the
        offline ``HashingEmbedder``.
    """

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder: Embedder = embedder or HashingEmbedder()
        self._ids: list[str] = []
        self._vectors: list[np.ndarray] = []
        self._records: dict[str, KnowledgeRecordV0] = {}

    def add(self, record: KnowledgeRecordV0) -> None:
        """Index a record by its content (and tags, for topical lift)."""
        if record.record_id in self._records:
            return
        text = record.content + " " + " ".join(record.topic_tags)
        self._ids.append(record.record_id)
        self._vectors.append(self._embedder.embed(text))
        self._records[record.record_id] = record

    def query(self, text: str, k: int = 5) -> list[tuple[KnowledgeRecordV0, float]]:
        """Return up to k (record, similarity) pairs ranked by cosine similarity."""
        if not self._vectors:
            return []
        q = self._embedder.embed(text)
        matrix = np.vstack(self._vectors)          # (N, dim), rows unit-norm
        sims = matrix @ q                          # cosine (q is unit-norm)
        order = np.argsort(-sims)[:k]
        results: list[tuple[KnowledgeRecordV0, float]] = []
        for idx in order:
            score = float(sims[idx])
            if math.isnan(score):
                continue
            results.append((self._records[self._ids[idx]], round(score, 4)))
        return results

    def count(self) -> int:
        return len(self._ids)

    @property
    def embedder_name(self) -> str:
        return type(self._embedder).__name__
