"""In-memory semantic index for Aura memory embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

try:  # NumPy is already available in the project, but keep a graceful fallback.
    import numpy as np
except Exception:  # pragma: no cover - fallback path
    np = None

from assistant.memory.models import MemoryEmbedding
from providers.embeddings.embeddingProvider import EmbeddingProvider


@dataclass
class IndexedEmbedding:
    """Embedding plus similarity metadata used during search."""

    embedding: MemoryEmbedding
    similarity: float


class SemanticMemoryIndex:
    """Maintain a fast, explainable in-memory semantic index."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.SemanticIndex") if logger else None
        self._embeddings: dict[str, MemoryEmbedding] = {}

    def rebuild(self, embeddings: list[MemoryEmbedding]):
        self._embeddings = {embedding.memoryId: embedding for embedding in embeddings}
        if self.logger:
            self.logger.info(f"Semantic index rebuilt with {len(self._embeddings)} item(s)")

    def add(self, embedding: MemoryEmbedding):
        self._embeddings[embedding.memoryId] = embedding

    def remove(self, memoryId: str):
        self._embeddings.pop(str(memoryId), None)

    def get(self, memoryId: str) -> MemoryEmbedding | None:
        return self._embeddings.get(str(memoryId))

    def all(self) -> list[MemoryEmbedding]:
        return list(self._embeddings.values())

    def search(self, queryVector: Iterable[float], limit: int = 5, minimumSimilarity: float = 0.65) -> list[IndexedEmbedding]:
        if not queryVector:
            return []
        ranked = []
        for embedding in self._embeddings.values():
            similarity = self._cosine(queryVector, embedding.vector)
            if similarity < float(minimumSimilarity):
                continue
            ranked.append(IndexedEmbedding(embedding=embedding, similarity=similarity))
        ranked.sort(key=lambda item: (item.similarity, item.embedding.updatedAt), reverse=True)
        return ranked[: int(limit)]

    def snapshot(self) -> dict[str, Any]:
        return {
            "indexedCount": len(self._embeddings),
            "embeddingIds": list(self._embeddings.keys()),
        }

    @staticmethod
    def _cosine(left: Iterable[float], right: Iterable[float]) -> float:
        leftValues = list(float(value) for value in left)
        rightValues = list(float(value) for value in right)
        if not leftValues or not rightValues or len(leftValues) != len(rightValues):
            return 0.0
        if np is not None:
            leftArray = np.asarray(leftValues, dtype=float)
            rightArray = np.asarray(rightValues, dtype=float)
            leftNorm = float(np.linalg.norm(leftArray))
            rightNorm = float(np.linalg.norm(rightArray))
            if not leftNorm or not rightNorm:
                return 0.0
            return float(np.dot(leftArray, rightArray) / (leftNorm * rightNorm))
        return EmbeddingProvider.cosineSimilarity(leftValues, rightValues)
