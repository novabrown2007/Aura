"""Embedding providers for Aura semantic memory."""

from __future__ import annotations

import hashlib
import math
from typing import Iterable


class EmbeddingProvider:
    """Small local embedding provider with no external dependency.

    The implementation uses hashed token buckets. It is deterministic, cheap,
    and good enough for local semantic ranking until a Chroma/FAISS-backed
    provider is plugged in behind this same interface.
    """

    def __init__(self, dimensions: int = 128):
        """Create a deterministic embedding provider."""

        self.dimensions = int(dimensions)

    def embedText(self, text: str) -> list[float]:
        """Embed text into a normalized numeric vector."""

        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            weight = 1.0 + (len(token) / 20.0)
            vector[index] += weight
        return self._normalize(vector)

    @staticmethod
    def cosineSimilarity(left: Iterable[float], right: Iterable[float]) -> float:
        """Return cosine similarity for two vectors."""

        leftValues = list(left)
        rightValues = list(right)
        if not leftValues or not rightValues or len(leftValues) != len(rightValues):
            return 0.0
        return sum(a * b for a, b in zip(leftValues, rightValues))

    @staticmethod
    def _tokens(text: str) -> list[str]:
        """Tokenize text for local embeddings."""

        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text))
        return [token for token in cleaned.split() if token]

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        """Normalize a vector to unit length."""

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
