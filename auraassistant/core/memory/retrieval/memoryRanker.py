"""Ranking for scored Aura memories."""

from __future__ import annotations

from auraassistant.core.memory.retrieval.relevanceScorer import ScoredMemory
from auraassistant.core.memory.tuning import RetrievalTuner


class MemoryRanker:
    """Sort memories by usefulness while preserving important context."""

    def __init__(self, tuner: RetrievalTuner, context=None):
        self.tuner = tuner
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Ranker") if logger else None

    def rank(self, scoredMemories: list[ScoredMemory]) -> list[ScoredMemory]:
        """Return memories ordered by injection usefulness."""

        ranked = sorted(
            scoredMemories,
            key=lambda item: (
                item.score,
                item.memory.importance,
                self.tuner.categoryWeights.get(item.memory.category, 1.0),
                item.memory.updatedAt,
            ),
            reverse=True,
        )
        if self.logger:
            self.logger.debug(f"Ranked {len(ranked)} scored memories")
        return ranked

