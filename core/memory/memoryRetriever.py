"""High-level retrieval API for Aura memories."""

from __future__ import annotations

from core.memory.indexing import MemoryIndex
from core.memory.memoryStore import MemoryStore
from core.memory.models import Memory, MemoryQuery
from core.memory.search import MemorySearchEngine


class MemoryRetriever:
    """Retrieve memories by category, tags, recency, importance, and keywords."""

    def __init__(self, store: MemoryStore, index: MemoryIndex, searchEngine: MemorySearchEngine, context=None):
        self.store = store
        self.index = index
        self.searchEngine = searchEngine
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Retriever") if logger else None

    def retrieve(self, query: MemoryQuery | None = None) -> list[Memory]:
        """Retrieve and rank memories."""

        query = query or MemoryQuery()
        if query.keywords or query.tags:
            storeQuery = MemoryQuery(
                categories=list(query.categories),
                minImportance=query.minImportance,
                limit=None,
                sessionId=query.sessionId,
                recentDays=query.recentDays,
            )
        else:
            storeQuery = query
        base = self.store.queryMemories(storeQuery)
        results = self.searchEngine.search(base, query) if query.keywords or query.tags else base
        if self.logger:
            self.logger.info(f"Retrieved {len(results)} memory item(s)")
        return results[: query.limit] if query.limit else results

    def byCategory(self, category: str, limit: int | None = None) -> list[Memory]:
        """Return memories in one category."""

        return self.retrieve(MemoryQuery(categories=[category], limit=limit))

    def byTags(self, tags: list[str], limit: int | None = None) -> list[Memory]:
        """Return memories matching any tag."""

        return self.retrieve(MemoryQuery(tags=tags, limit=limit))

    def recent(self, limit: int = 10) -> list[Memory]:
        """Return recent memories."""

        return self.retrieve(MemoryQuery(limit=limit))

    def important(self, threshold: float = 0.7, limit: int | None = None) -> list[Memory]:
        """Return important memories."""

        return self.retrieve(MemoryQuery(minImportance=threshold, limit=limit))

    def session(self, sessionId: str, limit: int | None = None) -> list[Memory]:
        """Return memories from a session."""

        return self.retrieve(MemoryQuery(sessionId=sessionId, limit=limit))

    def search(self, keywords: str, limit: int | None = None) -> list[Memory]:
        """Search by keyword/fuzzy matching."""

        return self.retrieve(MemoryQuery(keywords=keywords, limit=limit))
