"""Explainable importance scoring for Aura memories."""

from __future__ import annotations

from datetime import datetime, timezone


class MemoryScorer:
    """Score memory usefulness without ML ranking or embeddings."""

    explicitImportantTerms = {"important", "remember", "always", "never", "prefer", "preference", "working on"}

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Scorer") if logger else None

    def score(
        self,
        content: str,
        category: str,
        repetition: int = 1,
        explicitImportance: float | None = None,
        conversationalRelevance: float = 0.5,
        futureUsefulness: float | None = None,
        createdAt: str | None = None,
    ) -> float:
        """Return an importance score from 0.0 to 1.0."""

        if explicitImportance is not None:
            base = float(explicitImportance)
        else:
            lowered = str(content or "").lower()
            base = 0.35
            if any(term in lowered for term in self.explicitImportantTerms):
                base += 0.25
            if category in {"preferences", "projects", "people", "assistant_context", "system_context"}:
                base += 0.12

        repetitionBoost = min(max(repetition - 1, 0) * 0.06, 0.18)
        relevanceBoost = max(0.0, min(float(conversationalRelevance), 1.0)) * 0.15
        usefulness = 0.5 if futureUsefulness is None else max(0.0, min(float(futureUsefulness), 1.0))
        usefulnessBoost = usefulness * 0.18
        recencyBoost = self._recencyScore(createdAt) * 0.1
        score = max(0.0, min(base + repetitionBoost + relevanceBoost + usefulnessBoost + recencyBoost, 1.0))
        if self.logger:
            self.logger.debug(f"Scored memory category={category} score={score:.2f}")
        return score

    @staticmethod
    def _recencyScore(createdAt: str | None) -> float:
        if not createdAt:
            return 1.0
        try:
            created = datetime.fromisoformat(createdAt)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            ageDays = max((datetime.now(timezone.utc) - created).days, 0)
            return max(0.0, 1.0 - min(ageDays / 90.0, 1.0))
        except Exception:
            return 0.5

