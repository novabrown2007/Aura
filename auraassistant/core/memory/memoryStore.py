"""Storage protocol for Aura structured memories."""

from __future__ import annotations

from abc import ABC, abstractmethod

from auraassistant.core.memory.models import Memory, MemoryQuery


class MemoryStore(ABC):
    """Abstract persistence contract used by the memory manager."""

    @abstractmethod
    def upsertMemory(self, memory: Memory) -> Memory:
        """Create or update a memory."""

    @abstractmethod
    def getMemory(self, memoryId: str) -> Memory | None:
        """Return one memory by id."""

    @abstractmethod
    def deleteMemory(self, memoryId: str) -> bool:
        """Delete one memory by id."""

    @abstractmethod
    def queryMemories(self, query: MemoryQuery | None = None) -> list[Memory]:
        """Return memories matching the supplied query."""

    @abstractmethod
    def pruneMemories(self, minImportance: float, limit: int | None = None) -> int:
        """Remove low-importance memories and return the number removed."""

