"""Explainable relevance scoring for semantic memory results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from assistant.memory.models import SemanticMemoryQuery
from modules.llm.memory.models import Memory


class MemoryRelevanceScorer:
    """Combine semantic similarity, keyword match, importance, recency, and category relevance."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.SemanticScorer") if logger else None

    def score(
        self,
        memory: Memory,
        query: SemanticMemoryQuery,
        semanticSimilarity: float = 0.0,
        keywordScore: float = 0.0,
        keywordMatched: bool = False,
    ) -> tuple[float, str]:
        """Return a final relevance score and a human-readable explanation."""

        similarityWeight = float(query.similarityWeight or 0.0)
        recencyWeight = float(query.recencyWeight or 0.0)
        importanceWeight = float(query.importanceWeight or 0.0)
        similarityComponent = max(0.0, min(float(semanticSimilarity), 1.0)) * similarityWeight
        recencyComponent = self._recency(memory.updatedAt) * recencyWeight
        importanceComponent = max(0.0, min(float(memory.importance), 1.0)) * importanceWeight
        keywordComponent = min(max(float(keywordScore), 0.0), 1.0) * 0.15
        categoryComponent = self._categoryRelevance(memory.category, query.categories)
        matchedBonus = 0.05 if keywordMatched else 0.0
        score = max(0.0, min(similarityComponent + recencyComponent + importanceComponent + keywordComponent + categoryComponent + matchedBonus, 1.0))
        explanation = (
            f"semantic={semanticSimilarity:.2f}, "
            f"keyword={keywordScore:.2f}, "
            f"importance={memory.importance:.2f}, "
            f"recency={self._recency(memory.updatedAt):.2f}"
        )
        return score, explanation

    @staticmethod
    def _categoryRelevance(category: str, categories: Iterable[str]) -> float:
        categories = {str(item).strip().lower() for item in categories or [] if str(item).strip()}
        if not categories:
            return 0.0
        return 0.08 if str(category or "").strip().lower() in categories else 0.0

    @staticmethod
    def _recency(timestamp: str) -> float:
        try:
            parsed = datetime.fromisoformat(str(timestamp))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            days = max((datetime.now(timezone.utc) - parsed).days, 0)
            if days <= 1:
                return 1.0
            if days >= 120:
                return 0.05
            return max(0.05, 1.0 - (days / 120.0))
        except Exception:
            return 0.35
