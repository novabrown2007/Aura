"""Abstract embedding provider contract for Aura."""

from __future__ import annotations

from abc import ABC, abstractmethod
from math import sqrt
from typing import Iterable


class EmbeddingProvider(ABC):
    """Common contract for local or remote text embedding providers."""

    providerName = "base"
    modelName = ""
    vectorDimensions = 0

    def __init__(self, context=None):
        self.context = context
        self.logger = None
        self.initialized = False

    @abstractmethod
    def initialize(self):
        """Prepare provider resources."""

    @abstractmethod
    def embedText(self, text: str) -> list[float]:
        """Return one embedding vector for a text input."""

    def embedBatch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts using the provider's native or fallback path."""

        return [self.embedText(text) for text in texts]

    @abstractmethod
    def isAvailable(self) -> bool:
        """Return whether the provider can currently serve embeddings."""

    @abstractmethod
    def shutdown(self):
        """Release provider resources."""

    def metadata(self) -> dict[str, object]:
        """Return provider diagnostics for observability and UI surfaces."""

        return {
            "provider": self.providerName,
            "model": self.modelName,
            "dimensions": int(self.vectorDimensions or 0),
            "available": bool(self.isAvailable()),
            "initialized": bool(self.initialized),
        }

    @staticmethod
    def cosineSimilarity(left: Iterable[float], right: Iterable[float]) -> float:
        """Compute cosine similarity safely without requiring NumPy."""

        leftValues = [float(value) for value in left]
        rightValues = [float(value) for value in right]
        if not leftValues or not rightValues or len(leftValues) != len(rightValues):
            return 0.0
        dot = sum(a * b for a, b in zip(leftValues, rightValues))
        leftMagnitude = sqrt(sum(value * value for value in leftValues))
        rightMagnitude = sqrt(sum(value * value for value in rightValues))
        if not leftMagnitude or not rightMagnitude:
            return 0.0
        return max(0.0, min(dot / (leftMagnitude * rightMagnitude), 1.0))
