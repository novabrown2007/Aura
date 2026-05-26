"""Conversation-aware memory retrieval pipeline for Aura."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from modules.llm.memory.conversation import ConversationContextManager
from modules.llm.memory.injection import ContextCompressor, MemoryFormatter, PromptInjector
from modules.llm.memory.models import Memory, MemoryQuery
from modules.llm.memory.retrieval.contextWindowManager import ContextWindowManager
from modules.llm.memory.retrieval.memoryFilter import MemoryFilter
from modules.llm.memory.retrieval.memoryRanker import MemoryRanker
from modules.llm.memory.retrieval.relevanceScorer import RelevanceScorer, ScoredMemory
from modules.llm.memory.tuning import RetrievalTuner


@dataclass
class RetrievalResult:
    """Complete result and diagnostics for one retrieval pass."""

    retrievedMemories: list[Memory] = field(default_factory=list)
    scoredMemories: list[ScoredMemory] = field(default_factory=list)
    rankedMemories: list[ScoredMemory] = field(default_factory=list)
    filteredMemories: list[ScoredMemory] = field(default_factory=list)
    injectedMemories: list[ScoredMemory] = field(default_factory=list)
    overflowMemories: list[ScoredMemory] = field(default_factory=list)
    renderedLines: list[str] = field(default_factory=list)
    memorySection: str = ""
    tokenEstimate: int = 0
    debugOutput: str = ""


class ContextualRetriever:
    """Coordinate retrieval, scoring, ranking, filtering, compression, and injection."""

    def __init__(
        self,
        store,
        tuner: RetrievalTuner,
        conversationContext: ConversationContextManager,
        context=None,
    ):
        self.store = store
        self.tuner = tuner
        self.conversationContext = conversationContext
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.ContextualRetriever") if logger else None
        self.scorer = RelevanceScorer(tuner, context)
        self.ranker = MemoryRanker(tuner, context)
        self.filter = MemoryFilter(tuner, context)
        self.window = ContextWindowManager(tuner, context)
        self.compressor = ContextCompressor(context=context)
        self.formatter = MemoryFormatter(self.compressor, context)
        self.promptInjector = PromptInjector(self.formatter, context)
        self.recentlyInjectedIds = deque(maxlen=16)

    def retrieve(
        self,
        userMessage: str,
        conversationHistory: list | None = None,
        sessionId: str = "",
    ) -> RetrievalResult:
        """Run the full deterministic memory retrieval pipeline."""

        result = RetrievalResult()
        if not self.tuner.injectionEnabled:
            result.debugOutput = "[MEMORY RETRIEVAL]\nInjection disabled."
            return result

        try:
            context = self.conversationContext.buildContext(userMessage, conversationHistory)
            result.retrievedMemories = self.store.queryMemories(MemoryQuery())
            result.scoredMemories = [
                self.scorer.score(memory, userMessage, context, sessionId=sessionId)
                for memory in result.retrievedMemories
                if self._validMemory(memory)
            ]
            result.rankedMemories = self.ranker.rank(result.scoredMemories)
            rankedForInjection, repeated = self._filterRecentlyInjected(result.rankedMemories)
            kept, filtered = self.filter.filter(rankedForInjection)
            result.filteredMemories = filtered + repeated

            rendered = [
                self.formatter.formatMemory(
                    scored.memory,
                    maxCharacters=max(120, int(self.tuner.maxInjectionCharacters / max(self.tuner.maxInjectionCount, 1))),
                )
                for scored in kept
            ]
            result.injectedMemories, result.renderedLines, result.overflowMemories = self.window.fit(kept, rendered)
            result.memorySection = self.formatter.formatSection(result.renderedLines)
            result.tokenEstimate = self.window.estimateTokens(result.memorySection)
            for scored in result.injectedMemories:
                self.recentlyInjectedIds.append(scored.memory.memoryId)
            result.debugOutput = self._buildDebugOutput(result)
            if self.logger:
                self.logger.info(result.debugOutput)
            return result
        except Exception as error:
            result.debugOutput = f"[MEMORY RETRIEVAL]\nFailed: {error}"
            if self.logger:
                self.logger.warning(result.debugOutput)
            return result

    def injectPrompt(
        self,
        systemPrompt: str,
        userMessage: str,
        conversationHistory: list | None = None,
        sessionId: str = "",
    ) -> tuple[str, RetrievalResult]:
        """Retrieve context and inject it into a system prompt."""

        result = self.retrieve(userMessage, conversationHistory=conversationHistory, sessionId=sessionId)
        return self.promptInjector.inject(systemPrompt, result.memorySection), result

    def _filterRecentlyInjected(self, ranked: list[ScoredMemory]) -> tuple[list[ScoredMemory], list[ScoredMemory]]:
        kept = []
        repeated = []
        recentIds = set(self.recentlyInjectedIds)
        for scored in ranked:
            if scored.memory.memoryId in recentIds and scored.score < 0.7:
                repeated.append(scored)
                continue
            kept.append(scored)
        return kept, repeated

    @staticmethod
    def _validMemory(memory: Memory) -> bool:
        return bool(memory and memory.category and memory.content.strip())

    def _buildDebugOutput(self, result: RetrievalResult) -> str:
        top = result.rankedMemories[0] if result.rankedMemories else None
        lines = [
            "[MEMORY RETRIEVAL]",
            f"Retrieved: {len(result.retrievedMemories)} memories",
            f"Scored: {len(result.scoredMemories)} memories",
            f"Injected: {len(result.injectedMemories)} memories",
            f"Filtered: {len(result.filteredMemories) + len(result.overflowMemories)} memories",
            f"Token estimate: {result.tokenEstimate}",
        ]
        if top is not None:
            lines.extend(
                [
                    "",
                    "Top Memory:",
                    f'"{top.memory.title}"',
                    f"Score: {top.score:.2f}",
                    "Reasons: "
                    + ", ".join(f"{key}={value:.2f}" for key, value in sorted(top.reasons.items())),
                ]
            )
        if result.injectedMemories:
            lines.append("")
            lines.append("Injected Memories:")
            for scored in result.injectedMemories:
                lines.append(f"- {scored.memory.title} ({scored.memory.category}) score={scored.score:.2f}")
        return "\n".join(lines)
