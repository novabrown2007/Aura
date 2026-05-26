"""In-memory indexes for fast structured memory lookup."""

from __future__ import annotations

from collections import defaultdict

from modules.llm.memory.models import Memory


class MemoryIndex:
    """Maintain category, tag, and recency indexes for cached memories."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Index") if logger else None
        self.byId: dict[str, Memory] = {}
        self.byCategory: dict[str, set[str]] = defaultdict(set)
        self.byTag: dict[str, set[str]] = defaultdict(set)
        self.byRecency: list[str] = []

    def rebuild(self, memories: list[Memory]):
        """Rebuild all indexes from storage."""

        self.byId.clear()
        self.byCategory.clear()
        self.byTag.clear()
        for memory in memories:
            self.add(memory)
        self._sortRecency()
        if self.logger:
            self.logger.info(f"Memory index rebuilt with {len(self.byId)} item(s)")

    def add(self, memory: Memory):
        """Add or replace one memory in all indexes."""

        self.remove(memory.memoryId)
        self.byId[memory.memoryId] = memory
        self.byCategory[memory.category].add(memory.memoryId)
        for tag in memory.tags:
            self.byTag[tag].add(memory.memoryId)
        self._sortRecency()

    def remove(self, memoryId: str):
        """Remove one memory from all indexes."""

        existing = self.byId.pop(memoryId, None)
        if existing is None:
            return
        self.byCategory[existing.category].discard(memoryId)
        for tag in existing.tags:
            self.byTag[tag].discard(memoryId)
        self._sortRecency()

    def all(self) -> list[Memory]:
        """Return all indexed memories by recency."""

        return [self.byId[memoryId] for memoryId in self.byRecency if memoryId in self.byId]

    def category(self, category: str) -> list[Memory]:
        """Return memories for a category."""

        return [self.byId[memoryId] for memoryId in self.byCategory.get(category, set()) if memoryId in self.byId]

    def tag(self, tag: str) -> list[Memory]:
        """Return memories for a tag."""

        return [self.byId[memoryId] for memoryId in self.byTag.get(tag, set()) if memoryId in self.byId]

    def recent(self, limit: int = 10) -> list[Memory]:
        """Return recent memories."""

        return self.all()[: int(limit)]

    def _sortRecency(self):
        self.byRecency = [
            memory.memoryId
            for memory in sorted(self.byId.values(), key=lambda item: item.updatedAt, reverse=True)
        ]

