"""Semantic retrieval over Aura's stored memories."""

from __future__ import annotations

from typing import Any

from assistant.memory.memoryRelevanceScorer import MemoryRelevanceScorer
from assistant.memory.models import SemanticMemoryQuery, SemanticMemoryResult
from modules.llm.memory.models import Memory, MemoryQuery


class SemanticMemoryRetriever:
    """Retrieve memories by semantic similarity using the embedding index."""

    def __init__(self, memoryStore, embeddingIndex, embeddingManager, context=None, scorer=None):
        self.memoryStore = memoryStore
        self.embeddingIndex = embeddingIndex
        self.embeddingManager = embeddingManager
        self.context = context
        self.scorer = scorer or MemoryRelevanceScorer(context)
        self.lastSearch = {}
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.SemanticRetriever") if logger else None

    def retrieve(self, query: SemanticMemoryQuery, sessionContext: dict[str, Any] | None = None) -> list[SemanticMemoryResult]:
        """Return semantically relevant memories for a natural-language query."""

        if not query.queryText.strip():
            return []
        if self.embeddingManager is None or not getattr(self.embeddingManager, "available", False):
            self.lastSearch = {"available": False, "reason": "embedding-provider-unavailable"}
            return []

        queryVector = self.embeddingManager.embedText(query.queryText)
        if not queryVector:
            self.lastSearch = {"available": False, "reason": "embedding-generation-failed"}
            return []

        matches = self.embeddingIndex.search(queryVector, limit=max(int(query.maxResults), 1), minimumSimilarity=float(query.minimumSimilarity))
        queryTags = {str(tag).strip().lower() for tag in query.tags if str(tag).strip()}
        queryCategories = {str(category).strip().lower() for category in query.categories if str(category).strip()}
        results: list[SemanticMemoryResult] = []

        for match in matches:
            embedding = match.embedding
            memory = self.memoryStore.getMemory(embedding.memoryId) if hasattr(self.memoryStore, "getMemory") else None
            if memory is None:
                continue
            if queryCategories and memory.category not in queryCategories:
                continue
            if queryTags and not queryTags.intersection(set(memory.tags)):
                continue
            keywordScore = self._keywordOverlap(query.queryText, memory)
            relevanceScore, explanation = self.scorer.score(
                memory,
                query,
                semanticSimilarity=match.similarity,
                keywordScore=keywordScore,
                keywordMatched=keywordScore > 0,
            )
            if match.similarity < float(query.minimumSimilarity):
                continue
            results.append(
                SemanticMemoryResult(
                    memory=memory,
                    similarity=match.similarity,
                    relevanceScore=relevanceScore,
                    matchedBy="semantic",
                    explanation=explanation,
                )
            )

        results.sort(key=lambda item: (item.relevanceScore, item.similarity, item.memory.updatedAt), reverse=True)
        self.lastSearch = {
            "available": True,
            "queryText": query.queryText,
            "count": len(results),
            "minimumSimilarity": query.minimumSimilarity,
        }
        if self.logger:
            self.logger.debug(f"Semantic retrieval returned {len(results)} memory item(s)")
        return results[: int(query.maxResults)]

    def snapshot(self) -> dict[str, Any]:
        return dict(self.lastSearch)

    @staticmethod
    def _keywordOverlap(queryText: str, memory: Memory) -> float:
        queryTokens = SemanticMemoryRetriever._tokenize(queryText)
        memoryTokens = SemanticMemoryRetriever._tokenize(f"{memory.category} {memory.title} {memory.content} {' '.join(memory.tags)}")
        if not queryTokens or not memoryTokens:
            return 0.0
        return len(queryTokens.intersection(memoryTokens)) / float(max(len(queryTokens), 1))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text or ""))
        stop = {"the", "and", "for", "with", "that", "this", "from", "you", "are", "was", "were", "what", "i", "on"}
        return {token for token in cleaned.split() if len(token) > 1 and token not in stop}
