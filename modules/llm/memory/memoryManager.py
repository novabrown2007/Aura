"""Structured long-term memory manager for Aura."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from modules.llm.memory.conversation import ConversationContextManager
from modules.llm.memory.handlers.memoryEventHandler import MemoryEventHandler
from modules.llm.memory.injection import ContextCompressor, MemoryFormatter, PromptInjector
from modules.llm.memory.indexing import MemoryIndex
from modules.llm.memory.memoryInjector import MemoryInjector
from modules.llm.memory.memoryRetriever import MemoryRetriever
from modules.llm.memory.memoryScorer import MemoryScorer
from modules.llm.memory.memorySummarizer import MemorySummarizer
from modules.llm.memory.models import Memory, MemoryCategory, MemoryQuery
from modules.llm.memory.retrieval import ContextualRetriever, RetrievalResult
from modules.llm.memory.search import MemorySearchEngine
from modules.llm.memory.storage import SQLiteMemoryStore
from modules.llm.memory.tuning import RetrievalTuner
from modules.base import AuraModule, ModuleMetadata


class MemoryManager(AuraModule):
    """Coordinate storage, retrieval, summarization, injection, and indexing."""

    metadata = ModuleMetadata(
        name="memoryManager",
        version="2.0.0",
        description="Structured SQLite-backed long-term assistant memory.",
        permissions=("filesystem:read", "filesystem:write", "database:read", "database:write"),
        capabilities=("memory", "structured-memory", "conversation-continuity"),
    )

    secretPatterns = (
        re.compile(r"\b(password|passcode|token|api[_ -]?key|secret|credential|private key)\b", re.I),
        re.compile(r"\b(?:sk|pk|ghp|xoxb|AIza)[A-Za-z0-9_\-]{12,}\b"),
    )

    def __init__(self, context=None, store=None):
        super().__init__()
        self.context = context
        self.logger = None
        self.enabled = True
        self.maxResults = 8
        self.summaryLength = 280
        self.importanceThreshold = 0.35
        self.autoSummarization = True
        self.store = store
        self.index = None
        self.searchEngine = None
        self.scorer = None
        self.summarizer = None
        self.injector = None
        self.tuner = None
        self.conversationContext = None
        self.contextualRetriever = None
        self.contextCompressor = None
        self.memoryFormatter = None
        self.promptInjector = None
        self.lastRetrievalDebug = ""
        self.retriever = None
        self.eventHandler = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        """Initialize configured memory services."""

        super().initialize(context)
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory") if logger else None
        config = getattr(context, "config", None)
        self.enabled = bool(self._config(config, "memoryEnabled", self._config(config, "memory.enabled", True)))
        self.maxResults = int(self._config(config, "memoryMaxResults", self._config(config, "memory.maxResults", 8)))
        self.summaryLength = int(self._config(config, "memorySummaryLength", self._config(config, "memory.summaryLength", 280)))
        self.importanceThreshold = float(self._config(config, "memoryImportanceThreshold", self._config(config, "memory.importanceThreshold", 0.35)))
        self.autoSummarization = bool(self._config(config, "memoryAutoSummarization", self._config(config, "memory.autoSummarization", True)))
        databasePath = self._config(config, "memoryDatabasePath", self._config(config, "memory.databasePath", "aura_memory.sqlite3"))

        if self.store is None:
            self.store = SQLiteMemoryStore(str(Path(databasePath)), context=context)
        self.index = MemoryIndex(context)
        self.searchEngine = MemorySearchEngine(context)
        self.scorer = MemoryScorer(context)
        self.summarizer = MemorySummarizer(context, summaryLength=self.summaryLength)
        self.injector = MemoryInjector(context)
        self.tuner = RetrievalTuner(context)
        self.conversationContext = ConversationContextManager(context)
        self.contextualRetriever = ContextualRetriever(self.store, self.tuner, self.conversationContext, context)
        self.contextCompressor = ContextCompressor(context=context)
        self.memoryFormatter = MemoryFormatter(self.contextCompressor, context)
        self.promptInjector = PromptInjector(self.memoryFormatter, context)
        self.retriever = MemoryRetriever(self.store, self.index, self.searchEngine, context)
        self.rebuildIndex()

        self.eventHandler = MemoryEventHandler(context, self)
        self.eventHandler.subscribe()
        context.memoryManager = self
        if self.logger:
            self.logger.info("Structured memory manager initialized")

    def getIntents(self):
        """Return intents handled directly by memory manager."""

        return []

    def createMemory(
        self,
        category: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        importance: float | None = None,
        source: str = "manual",
        sessionId: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Memory | None:
        """Create and persist one structured memory."""

        if not self.enabled:
            return None
        if not self._isSafe(content) or not self._isSafe(title):
            if self.logger:
                self.logger.warning("Rejected unsafe memory content")
            return None
        category = MemoryCategory.normalize(category)
        score = self.scorer.score(content, category, explicitImportance=importance)
        memory = Memory(
            category=category,
            title=title,
            content=content,
            tags=tags or [],
            importance=score,
            source=source,
            sessionId=sessionId,
            metadata=metadata or {},
        )
        stored = self.store.upsertMemory(memory)
        self.index.add(stored)
        return stored

    def updateMemory(self, memoryId: str, **changes) -> Memory | None:
        """Update one memory by id."""

        memory = self.store.getMemory(memoryId)
        if memory is None:
            return None
        for key, value in changes.items():
            if key in {"title", "content"} and not self._isSafe(str(value)):
                return None
            if hasattr(memory, key):
                setattr(memory, key, value)
        updated = self.store.upsertMemory(Memory.fromDict(memory.asDict()))
        self.index.add(updated)
        return updated

    def deleteMemory(self, memoryId: str) -> bool:
        """Delete one memory."""

        deleted = self.store.deleteMemory(memoryId)
        if deleted:
            self.index.remove(memoryId)
        return deleted

    def retrieveMemories(self, query: MemoryQuery | None = None, **filters) -> list[Memory]:
        """Retrieve memories using a query object or keyword filters."""

        if query is None:
            query = MemoryQuery(**filters)
        if query.limit is None:
            query.limit = self.maxResults
        return self.retriever.retrieve(query)

    def searchMemories(self, keywords: str, limit: int | None = None) -> list[Memory]:
        """Search structured memories."""

        return self.retriever.search(keywords, limit=limit or self.maxResults)

    def summarizeConversation(self, messages, sessionId: str = "") -> Memory | None:
        """Summarize and store a completed conversation."""

        if not self.enabled or not self.autoSummarization:
            return None
        summary = self.summarizer.summarizeConversation(messages, sessionId=sessionId)
        if summary is None or not summary.summary:
            return None
        memory = self.createMemory(
            MemoryCategory.CONVERSATION_SUMMARIES.value,
            "Conversation summary",
            summary.summary,
            tags=summary.tags,
            source="conversation.ended",
            sessionId=sessionId,
            metadata=summary.asDict(),
        )
        for fact in summary.facts:
            category = self.summarizer.categorizeText(fact)
            if category:
                self.createMemory(category, self._titleFromContent(fact), fact, tags=summary.tags, source="conversation.fact", sessionId=sessionId)
        return memory

    def injectContext(self, userMessage: str, prompt: str = "", limit: int | None = None) -> str:
        """Inject relevant memories into a prompt."""

        injected, result = self.injectPrompt(prompt, userMessage, limit=limit)
        self.lastRetrievalDebug = result.debugOutput
        return injected

    def getContext(self, userMessage: str = "", limit: int | None = None, conversationHistory: list | None = None) -> dict[str, str]:
        """Return prompt-friendly contextual memory."""

        result = self.retrieveContext(userMessage, limit=limit, conversationHistory=conversationHistory)
        context = {}
        for scored in result.injectedMemories:
            memory = scored.memory
            key = f"{memory.category}.{self.injector._key(memory.title)}"
            context[key] = memory.content
        return context

    def retrieveContext(
        self,
        userMessage: str,
        limit: int | None = None,
        conversationHistory: list | None = None,
        sessionId: str = "",
    ) -> RetrievalResult:
        """Run tuned contextual retrieval and return full diagnostics."""

        if limit is not None:
            originalLimit = self.tuner.maxInjectionCount
            self.tuner.maxInjectionCount = int(limit)
            try:
                result = self.contextualRetriever.retrieve(userMessage, conversationHistory=conversationHistory, sessionId=sessionId)
            finally:
                self.tuner.maxInjectionCount = originalLimit
        else:
            result = self.contextualRetriever.retrieve(userMessage, conversationHistory=conversationHistory, sessionId=sessionId)
        self.lastRetrievalDebug = result.debugOutput
        return result

    def injectPrompt(
        self,
        prompt: str,
        userMessage: str,
        conversationHistory: list | None = None,
        sessionId: str = "",
        limit: int | None = None,
    ) -> tuple[str, RetrievalResult]:
        """Inject tuned memory context into a system prompt."""

        if limit is not None:
            result = self.retrieveContext(userMessage, limit=limit, conversationHistory=conversationHistory, sessionId=sessionId)
            injected = self.promptInjector.inject(prompt, result.memorySection)
        else:
            injected, result = self.contextualRetriever.injectPrompt(prompt, userMessage, conversationHistory=conversationHistory, sessionId=sessionId)
        self.lastRetrievalDebug = result.debugOutput
        return injected, result

    def learnFromMessage(self, text: str, sessionId: str = ""):
        """Extract obvious structured memories from a single user message."""

        memories = []
        for fact in self.summarizer.extractAtomicFacts(text):
            category = self.summarizer.categorizeText(fact)
            if not category:
                continue
            memory = self.createMemory(
                category,
                self._titleFromContent(fact),
                fact,
                tags=self.summarizer._extractTags(fact),
                source="message.received",
                sessionId=sessionId,
            )
            if memory is not None:
                memories.append(memory)
        return memories or None

    def learnFromHistory(self, messages: list[tuple[str, str]]):
        """Compatibility API for the old LLM memory manager."""

        return self.summarizeConversation(messages)

    def setMemory(self, key: str, value: str, importance: int = 1):
        """Compatibility helper that stores a preference/system memory."""

        score = max(0.0, min(float(importance) / 5.0, 1.0))
        existing = self._findLegacyMemory(key)
        if existing is not None:
            return self.updateMemory(existing.memoryId, content=value, importance=score, tags=[key])
        return self.createMemory("system_context", key, value, tags=[key], importance=score, source="legacy", metadata={"legacyKey": key})

    def setSemanticMemory(
        self,
        key: str,
        content: str,
        summary: str = "",
        memoryType: str = "fact",
        topics: list[str] | None = None,
        relationships: dict | None = None,
        importance: int = 1,
        source: str = "manual",
    ):
        """Compatibility helper for the retired semantic-memory API."""

        score = max(0.0, min(float(importance) / 5.0, 1.0))
        existing = self._findLegacyMemory(key)
        metadata = {
            "legacyKey": key,
            "summary": summary,
            "memoryType": memoryType,
            "relationships": relationships or {},
        }
        if existing is not None:
            return self.updateMemory(existing.memoryId, content=content, importance=score, tags=topics or [key], metadata=metadata)
        return self.createMemory("system_context", key, content, tags=topics or [key], importance=score, source=source, metadata=metadata)

    def retrieveRelevantMemories(self, query: str, limit: int | None = None) -> list[dict]:
        """Compatibility search API returning legacy-shaped dictionaries."""

        memories = self.searchMemories(query, limit=limit or self.maxResults)
        return [self._legacyDict(memory) for memory in memories]

    def summarizeMemories(self, query: str, limit: int | None = None) -> dict[str, str]:
        """Return relevant memories in prompt-ready key/value form."""

        if self.contextualRetriever is not None:
            result = self.retrieveContext(query, limit=limit or self.maxResults)
            memories = [scored.memory for scored in result.injectedMemories]
        else:
            memories = self.searchMemories(query, limit=limit or self.maxResults)
        result = {}
        for memory in memories:
            key = str(memory.metadata.get("legacyKey") or memory.title)
            result[key] = str(memory.metadata.get("summary") or memory.content)
        return result

    def getMemory(self):
        """Return prompt-ready memory dict for existing prompt builders."""

        memories = self.retrieveMemories(MemoryQuery(minImportance=self.importanceThreshold, limit=self.maxResults))
        result = {}
        for memory in memories:
            if memory.source == "legacy" or memory.metadata.get("legacyKey"):
                result[str(memory.metadata.get("legacyKey") or memory.title)] = memory.content
            else:
                result[f"{memory.category}.{self.injector._key(memory.title)}"] = memory.content
        return result

    def get(self, key: str):
        """Compatibility lookup by title/tag/id."""

        byId = self.store.getMemory(key)
        if byId:
            return byId.content
        legacy = self._findLegacyMemory(key)
        if legacy:
            return legacy.content
        for memory in self.searchMemories(key, limit=1):
            if memory.title == key or key in memory.tags:
                return memory.content
        return None

    def delete(self, key: str):
        """Compatibility delete by id or title."""

        memory = self.store.getMemory(key)
        if memory:
            return self.deleteMemory(key)
        for candidate in self.searchMemories(key, limit=10):
            if candidate.title == key or key in candidate.tags:
                return self.deleteMemory(candidate.memoryId)
        return False

    def clear(self):
        """Clear all memories."""

        for memory in self.store.queryMemories(MemoryQuery()):
            self.store.deleteMemory(memory.memoryId)
        self.rebuildIndex()

    def pruneMemories(self, minImportance: float | None = None, limit: int | None = None) -> int:
        """Remove low-importance memories."""

        removed = self.store.pruneMemories(minImportance if minImportance is not None else self.importanceThreshold, limit=limit)
        self.rebuildIndex()
        return removed

    def rebuildIndex(self):
        """Reload the in-memory index from storage."""

        if self.index is not None:
            self.index.rebuild(self.store.queryMemories(MemoryQuery()))

    def shutdown(self):
        """Close memory resources."""

        if self.eventHandler:
            self.eventHandler.unsubscribe()
        if hasattr(self.store, "close"):
            self.store.close()

    @classmethod
    def _isSafe(cls, text: str) -> bool:
        return not any(pattern.search(str(text or "")) for pattern in cls.secretPatterns)

    @staticmethod
    def _titleFromContent(content: str) -> str:
        cleaned = " ".join(str(content or "").split())
        return cleaned[:72].rstrip(".") or "Memory"

    def _findLegacyMemory(self, key: str) -> Memory | None:
        key = str(key or "")
        for memory in self.store.queryMemories(MemoryQuery()):
            if memory.title == key or memory.metadata.get("legacyKey") == key:
                return memory
        return None

    @staticmethod
    def _legacyDict(memory: Memory) -> dict:
        return {
            "memory_key": str(memory.metadata.get("legacyKey") or memory.title),
            "content": memory.content,
            "summary": str(memory.metadata.get("summary") or memory.content),
            "memory_type": str(memory.metadata.get("memoryType") or memory.category),
            "topics": list(memory.tags),
            "relationships": dict(memory.metadata.get("relationships") or {}),
            "importance": memory.importance,
            "score": memory.importance,
        }

    @staticmethod
    def _config(config, key: str, default=None):
        if config is None:
            return default
        return config.get(key, default)
