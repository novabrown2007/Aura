"""Filtering for memory injection candidates."""

from __future__ import annotations

from core.memory.retrieval.relevanceScorer import ScoredMemory
from core.memory.tuning import RetrievalTuner


class MemoryFilter:
    """Remove duplicates, low-value memories, and unrelated context."""

    def __init__(self, tuner: RetrievalTuner, context=None):
        self.tuner = tuner
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Filter") if logger else None

    def filter(self, scoredMemories: list[ScoredMemory]) -> tuple[list[ScoredMemory], list[ScoredMemory]]:
        """Return kept and filtered memories."""

        kept: list[ScoredMemory] = []
        removed: list[ScoredMemory] = []
        seen = set()
        for index, scored in enumerate(scoredMemories):
            memory = scored.memory
            if not memory.content.strip() or not memory.title.strip():
                removed.append(scored)
                continue
            if memory.category == "conversation_summaries" and scored.reasons.get("recency", 0.0) < 0.03 and scored.score < 0.4:
                removed.append(scored)
                continue
            if scored.score < self.tuner.minRelevance and memory.importance < 0.85:
                removed.append(scored)
                continue
            fingerprint = self._fingerprint(memory.content)
            if self.tuner.duplicateFiltering and fingerprint in seen:
                removed.append(scored)
                continue
            seen.add(fingerprint)
            kept.append(scored)
            if len(kept) >= self.tuner.maxInjectionCount:
                removed.extend(scoredMemories[index + 1:])
                break
        if self.logger:
            self.logger.debug(f"Filtered memories kept={len(kept)} removed={len(removed)}")
        return kept, removed

    @staticmethod
    def _fingerprint(text: str) -> str:
        cleaned = "".join(character.lower() if character.isalnum() else " " for character in str(text or ""))
        tokens = [token for token in cleaned.split() if len(token) > 2]
        return " ".join(tokens[:24])
