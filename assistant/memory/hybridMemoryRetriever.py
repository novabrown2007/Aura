"""Combine keyword and semantic memory retrieval."""

from __future__ import annotations

from typing import Any

from assistant.memory.models import SemanticMemoryQuery, SemanticMemoryResult
from modules.llm.memory.models import MemoryQuery


class HybridMemoryRetriever:
    """Merge lexical and semantic retrieval signals into one ranked result."""

    def __init__(self, memoryStore, memorySearchEngine, semanticRetriever, relevanceScorer, context=None):
        self.memoryStore = memoryStore
        self.memorySearchEngine = memorySearchEngine
        self.semanticRetriever = semanticRetriever
        self.relevanceScorer = relevanceScorer
        self.context = context
        self.lastDiagnostics: dict[str, Any] = {}
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.HybridRetriever") if logger else None

    def retrieve(self, queryText: str, sessionContext: dict[str, Any] | None = None, limit: int = 5) -> list[SemanticMemoryResult]:
        """Return memories ranked by a combined score."""

        query = SemanticMemoryQuery(
            queryText=str(queryText or ""),
            maxResults=max(int(limit or 5), 1),
            minimumSimilarity=self._minimumSimilarity(),
            recencyWeight=self._weight("semanticMemoryRecencyWeight", "memory.semantic.recencyWeight", 0.2),
            importanceWeight=self._weight("semanticMemoryImportanceWeight", "memory.semantic.importanceWeight", 0.2),
            similarityWeight=self._weight("semanticMemorySimilarityWeight", "memory.semantic.similarityWeight", 0.6),
        )
        semanticResults = self.semanticRetriever.retrieve(query, sessionContext=sessionContext) if self.semanticRetriever is not None else []
        semanticById = {result.memory.memoryId: result for result in semanticResults}

        keywordMemories = self.memoryStore.queryMemories(MemoryQuery(keywords=queryText, limit=None)) if hasattr(self.memoryStore, "queryMemories") else []
        keywordScores = {}
        for memory in keywordMemories:
            keywordScores[memory.memoryId] = self._keywordScore(queryText, memory)

        candidates = {}
        for result in semanticResults:
            candidates[result.memory.memoryId] = result
        for memory in keywordMemories:
            if memory.memoryId not in candidates:
                keywordScore = keywordScores.get(memory.memoryId, 0.0)
                score, explanation = self.relevanceScorer.score(
                    memory,
                    query,
                    semanticSimilarity=0.0,
                    keywordScore=keywordScore,
                    keywordMatched=keywordScore > 0,
                )
                candidates[memory.memoryId] = SemanticMemoryResult(
                    memory=memory,
                    similarity=0.0,
                    relevanceScore=score,
                    matchedBy="keyword",
                    explanation=explanation,
                )

        ranked = list(candidates.values())
        ranked.sort(key=lambda item: (item.relevanceScore, item.similarity, item.memory.updatedAt), reverse=True)
        ranked = ranked[: int(limit or 5)]
        self.lastDiagnostics = {
            "queryText": queryText,
            "semanticCount": len(semanticResults),
            "keywordCount": len(keywordMemories),
            "combinedCount": len(ranked),
            "semanticAvailable": bool(self.semanticRetriever is not None and getattr(self.semanticRetriever.embeddingManager, "available", False)),
        }
        if self.logger:
            self.logger.debug(
                f"Hybrid retrieval returned {len(ranked)} result(s) "
                f"(semantic={len(semanticResults)}, keyword={len(keywordMemories)})"
            )
        return ranked

    def snapshot(self) -> dict[str, Any]:
        return dict(self.lastDiagnostics)

    def _minimumSimilarity(self) -> float:
        return float(self._getConfigValue("semanticMemoryMinimumSimilarity", self._getConfigValue("memory.semantic.minimumSimilarity", 0.65)))

    def _weight(self, primary: str, fallback: str, default: float) -> float:
        return float(self._getConfigValue(primary, self._getConfigValue(fallback, default)))

    def _keywordScore(self, queryText: str, memory) -> float:
        if self.memorySearchEngine is None:
            return 0.0
        tokens = self.memorySearchEngine._tokenize(queryText)
        tags = set()
        return min(self.memorySearchEngine.scoreMemory(memory, tokens, tags), 4.0) / 4.0

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
