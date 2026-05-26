"""Context-window budget management for memory injection."""

from __future__ import annotations

from modules.llm.memory.retrieval.relevanceScorer import ScoredMemory
from modules.llm.memory.tuning import RetrievalTuner


class ContextWindowManager:
    """Keep injected memories inside count and character budgets."""

    def __init__(self, tuner: RetrievalTuner, context=None):
        self.tuner = tuner
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.ContextWindow") if logger else None

    def fit(self, scoredMemories: list[ScoredMemory], renderedLines: list[str]) -> tuple[list[ScoredMemory], list[str], list[ScoredMemory]]:
        """Return memories and rendered lines that fit configured budgets."""

        keptMemories: list[ScoredMemory] = []
        keptLines: list[str] = []
        overflow: list[ScoredMemory] = []
        used = 0
        for scored, line in zip(scoredMemories, renderedLines):
            length = len(line)
            if len(keptMemories) >= self.tuner.maxInjectionCount or used + length > self.tuner.maxInjectionCharacters:
                overflow.append(scored)
                continue
            keptMemories.append(scored)
            keptLines.append(line)
            used += length
        if self.logger:
            self.logger.debug(f"Memory context budget used {used}/{self.tuner.maxInjectionCharacters} characters")
        return keptMemories, keptLines, overflow

    @staticmethod
    def estimateTokens(text: str) -> int:
        """Return a cheap token estimate suitable for debug output."""

        return max(1, int(len(str(text or "")) / 4))

