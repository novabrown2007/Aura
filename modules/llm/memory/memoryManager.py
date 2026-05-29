"""Structured long-term memory manager for Aura."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from assistant.memory.hybridMemoryRetriever import HybridMemoryRetriever
from assistant.memory.memoryEmbeddingManager import MemoryEmbeddingManager
from assistant.memory.memoryInjector import MemoryInjector
from assistant.memory.memoryRelevanceScorer import MemoryRelevanceScorer
from assistant.memory.semanticMemoryIndex import SemanticMemoryIndex
from assistant.memory.semanticMemoryRetriever import SemanticMemoryRetriever
from assistant.memory.storage import SQLiteEmbeddingStore
from modules.llm.memory.conversation import ConversationContextManager
from modules.llm.memory.handlers.memoryEventHandler import MemoryEventHandler
from modules.llm.memory.injection import ContextCompressor, MemoryFormatter, PromptInjector
from modules.llm.memory.indexing import MemoryIndex
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
        self.semanticMemoryEnabled = True
        self.semanticMemoryMaxResults = 5
        self.semanticMemoryMinimumSimilarity = 0.65
        self.semanticMemoryRecencyWeight = 0.2
        self.semanticMemoryImportanceWeight = 0.2
        self.semanticMemorySimilarityWeight = 0.6
        self.semanticMemoryAutoIndex = True
        self.semanticMemoryIndex = None
        self.semanticMemoryStore = None
        self.memoryEmbeddingManager = None
        self.semanticMemoryRetriever = None
        self.hybridMemoryRetriever = None
        self.semanticMemoryScorer = None
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
        self.semanticMemoryEnabled = bool(self._config(config, "semanticMemoryEnabled", self._config(config, "memory.semantic.enabled", True)))
        self.semanticMemoryMaxResults = int(self._config(config, "semanticMemoryMaxResults", self._config(config, "memory.semantic.maxResults", 5)))
        self.semanticMemoryMinimumSimilarity = float(self._config(config, "semanticMemoryMinimumSimilarity", self._config(config, "memory.semantic.minimumSimilarity", 0.65)))
        self.semanticMemoryRecencyWeight = float(self._config(config, "semanticMemoryRecencyWeight", self._config(config, "memory.semantic.recencyWeight", 0.2)))
        self.semanticMemoryImportanceWeight = float(self._config(config, "semanticMemoryImportanceWeight", self._config(config, "memory.semantic.importanceWeight", 0.2)))
        self.semanticMemorySimilarityWeight = float(self._config(config, "semanticMemorySimilarityWeight", self._config(config, "memory.semantic.similarityWeight", 0.6)))
        self.semanticMemoryAutoIndex = bool(self._config(config, "semanticMemoryAutoIndex", self._config(config, "memory.semantic.autoIndex", True)))

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
        self.semanticMemoryStore = SQLiteEmbeddingStore(str(Path(databasePath)), context=context)
        self.semanticMemoryIndex = SemanticMemoryIndex(context)
        self.semanticMemoryScorer = MemoryRelevanceScorer(context)
        self.memoryEmbeddingManager = MemoryEmbeddingManager(
            context,
            store=self.semanticMemoryStore,
            index=self.semanticMemoryIndex,
        )
        self.semanticMemoryRetriever = SemanticMemoryRetriever(
            self.store,
            self.semanticMemoryIndex,
            self.memoryEmbeddingManager,
            context,
            scorer=self.semanticMemoryScorer,
        )
        self.hybridMemoryRetriever = HybridMemoryRetriever(
            self.store,
            self.searchEngine,
            self.semanticMemoryRetriever,
            self.semanticMemoryScorer,
            context,
        )
        self._compactStoredMemories()
        self.rebuildIndex()
        if self.semanticMemoryAutoIndex:
            self.memoryEmbeddingManager.reindexAll(self.store.queryMemories(MemoryQuery()))

        self.eventHandler = MemoryEventHandler(context, self)
        self.eventHandler.subscribe()
        context.memoryManager = self
        self._logStartup("memoryManager module started.")

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
        category, title, content, tags = self._normalizeMemoryCandidate(category, title, content, tags)
        if self._shouldRejectMemory(title, content):
            if self.logger:
                self.logger.debug(f"Rejected non-durable memory candidate: {title}")
            return None
        category = MemoryCategory.normalize(category)
        score = self.scorer.score(content, category, explicitImportance=importance)
        existing = self._findDuplicateMemory(category, title, content)
        if existing is not None:
            sameContent = self._memoryFingerprint(existing.content) == self._memoryFingerprint(content)
            mergedTags = sorted(set(existing.tags).union(str(tag).strip().lower() for tag in (tags or []) if str(tag).strip()))
            mergedMetadata = dict(existing.metadata or {})
            mergedMetadata.update(metadata or {})
            return self.updateMemory(
                existing.memoryId,
                title=existing.title if sameContent else title,
                content=existing.content if sameContent else content,
                tags=mergedTags,
                importance=max(existing.importance, score),
                source=source or existing.source,
                metadata=mergedMetadata,
            )
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
        if self.semanticMemoryEnabled and self.semanticMemoryAutoIndex and self.memoryEmbeddingManager is not None:
            self.memoryEmbeddingManager.indexMemory(stored)
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
        if self.semanticMemoryEnabled and self.semanticMemoryAutoIndex and self.memoryEmbeddingManager is not None:
            self.memoryEmbeddingManager.refreshMemory(updated)
        return updated

    def deleteMemory(self, memoryId: str) -> bool:
        """Delete one memory."""

        deleted = self.store.deleteMemory(memoryId)
        if deleted:
            self.index.remove(memoryId)
            if self.memoryEmbeddingManager is not None:
                self.memoryEmbeddingManager.removeMemory(memoryId)
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

        relevant = self.retrieveRelevantMemories(userMessage, limit=limit or self.maxResults, sessionContext={"conversationHistory": conversationHistory or []})
        context = {}
        for item in relevant:
            memoryDict = dict(item.get("memory") or {})
            if not memoryDict:
                memoryDict = {
                    "category": str(item.get("memory_type") or item.get("category") or "system_context"),
                    "title": str(item.get("memory_key") or item.get("summary") or item.get("content") or "Memory"),
                    "content": str(item.get("content") or item.get("summary") or ""),
                    "tags": list(item.get("topics") or []),
                    "importance": float(item.get("importance") or 0.0),
                    "source": "legacy",
                    "metadata": {
                        "legacyKey": item.get("memory_key") or item.get("title") or "",
                        "summary": item.get("summary") or item.get("content") or "",
                        "memoryType": item.get("memory_type") or item.get("category") or "",
                        "relationships": dict(item.get("relationships") or {}),
                    },
                }
            memory = Memory.fromDict(memoryDict)
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

        if self.semanticMemoryEnabled and self.hybridMemoryRetriever is not None:
            injected, result = self.injector.injectIntoPrompt(
                prompt,
                userMessage,
                conversationHistory=conversationHistory,
                sessionId=sessionId,
                limit=limit or self.semanticMemoryMaxResults,
            )
            if getattr(result, "memorySection", ""):
                self.lastRetrievalDebug = result.debugOutput
                return injected, result
            if limit is not None:
                result = self.retrieveContext(userMessage, limit=limit, conversationHistory=conversationHistory, sessionId=sessionId)
                injected = self.promptInjector.inject(prompt, result.memorySection)
            else:
                injected, result = self.contextualRetriever.injectPrompt(
                    prompt,
                    userMessage,
                    conversationHistory=conversationHistory,
                    sessionId=sessionId,
                )
            self.lastRetrievalDebug = result.debugOutput
            return injected, result
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

    def retrieveRelevantMemories(self, query: str, limit: int | None = None, sessionContext: dict | None = None) -> list[dict]:
        """Compatibility search API returning legacy-shaped dictionaries."""

        sessionContext = sessionContext or {"sessionId": ""}
        if self.semanticMemoryEnabled and self.hybridMemoryRetriever is not None:
            results = self.hybridMemoryRetriever.retrieve(query, sessionContext=sessionContext, limit=limit or self.semanticMemoryMaxResults)
            self._updateSemanticDiagnostics(query, results)
            return [
                {
                    "memory": result.memory.asDict(),
                    "memory_key": str(result.memory.metadata.get("legacyKey") or result.memory.title),
                    "content": result.memory.content,
                    "summary": str(result.memory.metadata.get("summary") or result.memory.content),
                    "memory_type": str(result.memory.metadata.get("memoryType") or result.memory.category),
                    "topics": list(result.memory.tags),
                    "relationships": dict(result.memory.metadata.get("relationships") or {}),
                    "importance": result.memory.importance,
                    "score": result.relevanceScore,
                    "similarity": result.similarity,
                    "relevanceScore": result.relevanceScore,
                    "matchedBy": result.matchedBy,
                    "explanation": result.explanation,
                }
                for result in results
            ]
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

    def snapshot(self) -> dict[str, Any]:
        """Return runtime diagnostics for observability and developer UI surfaces."""

        memoryState = {
            "enabled": bool(self.enabled),
            "storedCount": self.store.count() if hasattr(self.store, "count") else 0,
            "semantic": self.semanticMemoryState(),
        }
        return memoryState

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
        if self.semanticMemoryStore is not None:
            self.semanticMemoryStore.clear()
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
        if self.semanticMemoryEnabled and self.memoryEmbeddingManager is not None:
            self.memoryEmbeddingManager.reindexAll(self.store.queryMemories(MemoryQuery()))

    def _compactStoredMemories(self):
        """Remove invalid question memories and merge exact duplicate facts."""

        if self.store is None:
            return
        seen: dict[tuple[str, str], Memory] = {}
        for memory in self.store.queryMemories(MemoryQuery()):
            original = memory.asDict()
            category, title, content, tags = self._normalizeMemoryCandidate(
                memory.category,
                memory.title,
                memory.content,
                memory.tags,
            )
            memory.category = category
            memory.title = title
            memory.content = content
            memory.tags = tags
            if memory.asDict() != original:
                self.store.upsertMemory(memory)
            if self._shouldRejectMemory(memory.title, memory.content):
                self.store.deleteMemory(memory.memoryId)
                continue
            key = self._dedupeKey(memory)
            if not key[1]:
                continue
            existing = seen.get(key)
            if existing is None:
                seen[key] = memory
                continue
            preferNewer = self._memoryFingerprint(existing.content) != self._memoryFingerprint(memory.content)
            keep, remove = self._chooseMemoryToKeep(existing, memory, preferNewer=preferNewer)
            mergedTags = sorted(set(keep.tags).union(remove.tags))
            mergedMetadata = dict(remove.metadata or {})
            mergedMetadata.update(keep.metadata or {})
            keep.tags = mergedTags
            keep.importance = max(keep.importance, remove.importance)
            keep.metadata = mergedMetadata
            self.store.upsertMemory(keep)
            self.store.deleteMemory(remove.memoryId)
            seen[key] = keep
        self._compactConversationSummaries()

    def shutdown(self):
        """Close memory resources."""

        if self.eventHandler:
            self.eventHandler.unsubscribe()
        if self.memoryEmbeddingManager is not None:
            self.memoryEmbeddingManager.shutdown()
        if hasattr(self.store, "close"):
            self.store.close()

    @classmethod
    def _isSafe(cls, text: str) -> bool:
        return not any(pattern.search(str(text or "")) for pattern in cls.secretPatterns)

    @staticmethod
    def _titleFromContent(content: str) -> str:
        cleaned = " ".join(str(content or "").split())
        return cleaned[:72].rstrip(".") or "Memory"

    def _findDuplicateMemory(self, category: str, title: str, content: str) -> Memory | None:
        fingerprint = self._memoryFingerprint(content)
        titleFingerprint = self._memoryFingerprint(title)
        if not fingerprint and not titleFingerprint:
            return None
        for memory in self.store.queryMemories(MemoryQuery(categories=[category])):
            if fingerprint and self._memoryFingerprint(memory.content) == fingerprint:
                return memory
            if titleFingerprint and self._memoryFingerprint(memory.title) == titleFingerprint:
                return memory
        return None

    @classmethod
    def _normalizeMemoryCandidate(
        cls,
        category: str,
        title: str,
        content: str,
        tags: list[str] | None,
    ) -> tuple[str, str, str, list[str]]:
        category = MemoryCategory.normalize(category)
        title = str(title or "").strip()
        content = str(content or "").strip()
        normalizedTags = sorted({str(tag).strip().lower() for tag in (tags or []) if str(tag).strip()})

        name = cls._extractNameFact(f"{title}\n{content}")
        if name:
            return "people", "Name", f"Nova's name is {name}.", sorted(set(normalizedTags).union({"profile", "name"}))
        return category, title, content, normalizedTags

    @staticmethod
    def _extractNameFact(text: str) -> str:
        match = re.search(r"\b(?:my|nova's)\s+name\s+is\s+([a-zA-Z][a-zA-Z .'-]{1,80})", str(text or ""), flags=re.IGNORECASE)
        if not match:
            return ""
        words = []
        for word in match.group(1).strip(" .,\n\t").split():
            if word.lower() in {"and", "but", "so"}:
                break
            words.append(word)
        return " ".join(words)

    @classmethod
    def _shouldRejectMemory(cls, title: str, content: str) -> bool:
        text = " ".join(str(value or "").strip() for value in (title, content) if str(value or "").strip())
        if not text:
            return True
        return cls._looksLikeQuestion(str(title or "")) or cls._looksLikeQuestion(str(content or ""))

    @staticmethod
    def _looksLikeQuestion(text: str) -> bool:
        lowered = str(text or "").strip().lower()
        if not lowered:
            return False
        if lowered.endswith("?"):
            return True
        return bool(
            re.match(
                r"^(what|who|when|where|why|how|do|does|did|can|could|would|should|is|are|am)\b",
                lowered,
            )
        )

    @staticmethod
    def _memoryFingerprint(text: str) -> str:
        lowered = str(text or "").lower()
        lowered = lowered.replace("non-binaring", "non-binary").replace("nonbinary", "non-binary")
        lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
        return " ".join(lowered.split())

    @staticmethod
    def _chooseMemoryToKeep(first: Memory, second: Memory, preferNewer: bool = False) -> tuple[Memory, Memory]:
        if second.importance > first.importance:
            return second, first
        if second.importance == first.importance:
            if preferNewer:
                if second.createdAt > first.createdAt:
                    return second, first
            elif second.createdAt < first.createdAt:
                return second, first
        return first, second

    @classmethod
    def _dedupeKey(cls, memory: Memory) -> tuple[str, str]:
        titleFingerprint = cls._memoryFingerprint(memory.title)
        if memory.category in {"people", "preferences"} and (
            "profile" in memory.tags
            or titleFingerprint
            in {
                "name",
                "birthday",
                "age",
                "relationship orientation",
                "gender identity",
                "sexual orientation",
            }
        ):
            return memory.category, titleFingerprint
        return memory.category, cls._memoryFingerprint(memory.content)

    def _compactConversationSummaries(self):
        summaries = [
            memory
            for memory in self.store.queryMemories(MemoryQuery(categories=[MemoryCategory.CONVERSATION_SUMMARIES.value]))
            if self._memoryFingerprint(memory.content)
        ]
        for candidate in summaries:
            candidateText = self._memoryFingerprint(candidate.content)
            for other in summaries:
                if candidate.memoryId == other.memoryId:
                    continue
                otherText = self._memoryFingerprint(other.content)
                if len(candidateText) < len(otherText) and candidateText in otherText:
                    self.store.deleteMemory(candidate.memoryId)
                    break

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

    def semanticMemoryState(self) -> dict[str, Any]:
        """Return semantic memory diagnostics for observability and UI use."""

        state = self.memoryEmbeddingManager.snapshot() if self.memoryEmbeddingManager is not None else {"available": False, "enabled": False}
        state["lastSearch"] = dict(getattr(self.hybridMemoryRetriever, "snapshot", lambda: {})())
        return state

    def _updateSemanticDiagnostics(self, query: str, results):
        if self.memoryEmbeddingManager is not None:
            self.memoryEmbeddingManager.lastSearchText = str(query or "")
        if self.hybridMemoryRetriever is not None:
            self.hybridMemoryRetriever.lastDiagnostics["queryText"] = str(query or "")

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Memory event emission failed for {eventName}: {error}")
        return None

    @staticmethod
    def _config(config, key: str, default=None):
        if config is None:
            return default
        return config.get(key, default)
