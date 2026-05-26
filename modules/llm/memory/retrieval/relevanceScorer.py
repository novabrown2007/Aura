"""Deterministic relevance scoring for Aura memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from modules.llm.memory.models import Memory
from modules.llm.memory.tuning import RetrievalTuner


@dataclass
class ScoredMemory:
    """A memory with explainable retrieval score details."""

    memory: Memory
    score: float
    reasons: dict[str, float] = field(default_factory=dict)


class RelevanceScorer:
    """Score memories using lexical, category, recency, and continuity signals."""

    def __init__(self, tuner: RetrievalTuner, context=None):
        self.tuner = tuner
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Relevance") if logger else None

    def score(self, memory: Memory, userMessage: str, conversationContext: dict | None = None, sessionId: str = "") -> ScoredMemory:
        """Return an explainable score for one memory."""

        conversationContext = conversationContext or {}
        messageTokens = self._tokenize(userMessage)
        memoryTokens = self._tokenize(f"{memory.category} {memory.title} {memory.content} {' '.join(memory.tags)}")
        activeTopics = set(conversationContext.get("activeTopics") or [])
        recentTokens = set(conversationContext.get("recentTokens") or [])

        keywordScore = self._overlap(messageTokens, memoryTokens)
        tagScore = self._overlap(messageTokens.union(activeTopics), set(memory.tags))
        categoryScore = self.tuner.categoryWeights.get(memory.category, 1.0) / max(self.tuner.categoryWeights.values() or [1.0])
        recencyScore = self._recency(memory.updatedAt)
        importanceScore = memory.importance
        sessionScore = 1.0 if sessionId and memory.sessionId == sessionId else 0.0
        continuityScore = self._overlap(activeTopics.union(recentTokens), memoryTokens)

        reasons = {
            "keyword": keywordScore * 0.28,
            "tag": tagScore * 0.12,
            "category": categoryScore * 0.08,
            "recency": recencyScore * self.tuner.recencyWeight,
            "importance": importanceScore * self.tuner.importanceWeight,
            "session": sessionScore * 0.08,
            "continuity": continuityScore * 0.22,
        }
        score = max(0.0, min(sum(reasons.values()), 1.0))
        return ScoredMemory(memory=memory, score=score, reasons=reasons)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text or ""))
        stop = {"the", "and", "for", "with", "that", "this", "from", "you", "are", "was", "were"}
        return {token for token in cleaned.split() if len(token) > 1 and token not in stop}

    @staticmethod
    def _overlap(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left.intersection(right)) / float(max(len(left), 1))

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

