"""Semantic memory injection for Aura prompts."""

from __future__ import annotations

from modules.llm.memory.models import Memory
from modules.llm.memory.retrieval.relevanceScorer import ScoredMemory
from modules.llm.memory.retrieval.contextualRetriever import RetrievalResult


class MemoryInjector:
    """Prepare concise semantic memory context for LLM prompts."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Injector") if logger else None

    def retrieveRelevantMemories(self, userInput: str, sessionContext: dict | None = None, limit: int | None = None):
        """Request semantically relevant memories from the active memory manager."""

        manager = getattr(self.context, "memoryManager", None)
        if manager is None or not hasattr(manager, "retrieveRelevantMemories"):
            return []
        return manager.retrieveRelevantMemories(userInput, limit=limit, sessionContext=sessionContext)

    def injectIntoPrompt(
        self,
        prompt: str,
        userInput: str,
        conversationHistory: list | None = None,
        sessionId: str = "",
        limit: int | None = None,
    ):
        """Inject concise semantic memory context into a system prompt."""

        manager = getattr(self.context, "memoryManager", None)
        sessionContext = self._buildSessionContext(conversationHistory, sessionId)
        relevant = self.retrieveRelevantMemories(userInput, sessionContext=sessionContext, limit=limit)
        result = RetrievalResult()
        result.retrievedMemories = []
        result.scoredMemories = []
        result.rankedMemories = []
        result.filteredMemories = []
        result.injectedMemories = []
        result.overflowMemories = []
        result.renderedLines = []

        if not relevant:
            result.memorySection = ""
            result.debugOutput = "[MEMORY RETRIEVAL]\nRetrieved: 0 memories\nInjected: 0 memories"
            result.tokenEstimate = 0
            return prompt, result

        lines = ["Relevant Context:"]
        for item in relevant[: int(limit or len(relevant))]:
            memoryDict = dict(item.get("memory") or {})
            memory = Memory.fromDict(memoryDict)
            lines.append(
                f"- [{memory.category}] {memory.title} "
                f"(score={float(item.get('relevanceScore') or 0.0):.2f}, similarity={float(item.get('similarity') or 0.0):.2f})"
            )
            lines.append(f"  {memory.content}")
            explanation = str(item.get("explanation") or "").strip()
            if explanation:
                lines.append(f"  Why: {explanation}")
            scored = ScoredMemory(memory=memory, score=float(item.get("relevanceScore") or 0.0), reasons={"semantic": float(item.get("similarity") or 0.0)})
            result.retrievedMemories.append(memory)
            result.scoredMemories.append(scored)
            result.rankedMemories.append(scored)
            result.injectedMemories.append(scored)
            result.renderedLines.append(
                f"- [{memory.category}] {memory.title} (score={float(item.get('relevanceScore') or 0.0):.2f}, similarity={float(item.get('similarity') or 0.0):.2f})"
            )

        result.memorySection = "\n".join(lines)
        result.tokenEstimate = max(1, len(result.memorySection) // 4)
        result.debugOutput = (
            "[MEMORY RETRIEVAL]\n"
            f"Retrieved: {len(relevant)} memories\n"
            f"Injected: {len(result.injectedMemories)} memories\n"
            f"Semantic: {getattr(manager, 'semanticMemoryEnabled', False)}\n"
            f"Provider: {getattr(getattr(manager, 'memoryEmbeddingManager', None), 'snapshot', lambda: {})().get('provider', 'unknown') if manager else 'unknown'}"
        )
        if self.logger:
            self.logger.info(f"Injected {len(result.injectedMemories)} semantic memory item(s)")
        promptText = str(prompt or "").rstrip()
        if not result.memorySection:
            return promptText, result
        return f"{promptText}\n\n{result.memorySection}", result

    def buildContext(self, memories: list[Memory], maxItems: int = 8) -> dict[str, str]:
        """Return a compact prompt-friendly memory context map."""

        context = {}
        for memory in memories[: int(maxItems)]:
            key = f"{memory.category}.{self._key(memory.title)}"
            context[key] = memory.content
        return context

    @staticmethod
    def _buildSessionContext(conversationHistory: list | None, sessionId: str) -> dict:
        return {
            "conversationHistory": conversationHistory or [],
            "sessionId": str(sessionId or ""),
        }

    @staticmethod
    def _key(title: str) -> str:
        cleaned = "".join(character.lower() if character.isalnum() else "_" for character in str(title or "memory"))
        return "_".join(part for part in cleaned.split("_") if part)[:64] or "memory"
