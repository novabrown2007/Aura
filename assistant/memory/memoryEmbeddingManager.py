"""Manage embedding generation and index maintenance for Aura memories."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from assistant.memory.models import MemoryEmbedding
from assistant.memory.storage import SQLiteEmbeddingStore
from providers.embeddings import GeminiEmbeddingProvider, LocalEmbeddingProvider


class MemoryEmbeddingManager:
    """Coordinate provider selection, embedding generation, and persistence."""

    def __init__(self, context=None, store: SQLiteEmbeddingStore | None = None, provider=None, index=None):
        self.context = context
        self.store = store
        self.provider = provider
        self.index = index
        self.enabled = True
        self.available = False
        self.lastIndexAt = ""
        self.lastSearchText = ""
        self.lastError = ""
        self._indexedCount = 0
        self._failedCount = 0
        self.logger = None
        if context is not None:
            self.initialize(context)

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        logger = getattr(self.context, "logger", None)
        self.logger = logger.getChild("Memory.Embeddings") if logger else None
        config = getattr(self.context, "config", None)
        self.enabled = bool(self._getConfigValue(config, "semanticMemoryEnabled", self._getConfigValue(config, "memory.semantic.enabled", True)))
        databasePath = self._getConfigValue(config, "memory.databasePath", "aura_memory.sqlite3")
        if self.store is None:
            self.store = SQLiteEmbeddingStore(str(databasePath), context=self.context)
        if self.provider is None:
            self.provider = self._buildProvider(config)
        if self.provider is not None and hasattr(self.provider, "initialize"):
            self.provider.initialize()
        self.available = bool(self.enabled and self.provider is not None and getattr(self.provider, "isAvailable", lambda: False)())
        if self.index is not None and hasattr(self.index, "rebuild"):
            self.index.rebuild(self.store.listEmbeddings())
        self._indexedCount = self.store.count()
        return self

    def indexMemory(self, memory):
        """Create or update one memory embedding."""

        if not self.enabled or not self.available or memory is None:
            return None
        try:
            vector = self.embedText(self._embeddingText(memory))
            if not vector:
                return None
            now = self._now()
            existing = self.store.getEmbeddingByMemoryId(memory.memoryId)
            embedding = MemoryEmbedding(
                memoryId=str(memory.memoryId),
                provider=str(getattr(self.provider, "providerName", "unknown")),
                model=str(getattr(self.provider, "modelName", "") or getattr(self.provider, "model", "") or ""),
                vector=list(vector),
                createdAt=str(existing.createdAt if existing is not None else now),
                updatedAt=now,
                metadata={
                    "title": memory.title,
                    "category": memory.category,
                    "source": memory.source,
                    "tags": list(memory.tags),
                },
            )
            self.store.upsertEmbedding(embedding)
            if self.index is not None:
                self.index.add(embedding)
            self._indexedCount = self.store.count()
            self.lastIndexAt = now
            self._emit("memory.embedding.created" if existing is None else "memory.embedding.updated", embedding.asDict())
            return embedding
        except Exception as error:
            self.available = False
            self.lastError = str(error)
            self._failedCount += 1
            self._emit("memory.embedding.updated", {"memoryId": getattr(memory, "memoryId", ""), "error": str(error)})
            if self.logger:
                self.logger.warning(f"Memory embedding failed: {error}")
            return None

    def refreshMemory(self, memory):
        """Refresh one memory embedding when the source row changes."""

        return self.indexMemory(memory)

    def removeMemory(self, memoryId: str):
        """Delete one memory embedding."""

        deleted = self.store.deleteEmbedding(memoryId)
        if self.index is not None:
            self.index.remove(memoryId)
        self._indexedCount = self.store.count()
        return deleted

    def reindexAll(self, memories: list):
        """Rebuild all semantic embeddings from structured memories."""

        if not self.enabled:
            return []
        results = []
        for memory in memories or []:
            embedding = self.indexMemory(memory)
            if embedding is not None:
                results.append(embedding)
        if self.index is not None:
            self.index.rebuild(self.store.listEmbeddings())
        self.lastIndexAt = self._now()
        return results

    def refreshStaleEmbeddings(self, memories: list):
        """Refresh embeddings whose source memories are newer than the stored vector."""

        refreshed = []
        for memory in memories or []:
            existing = self.store.getEmbeddingByMemoryId(memory.memoryId)
            if existing is None or str(existing.updatedAt or "") < str(memory.updatedAt or ""):
                refreshed.append(self.indexMemory(memory))
        return [item for item in refreshed if item is not None]

    def embedText(self, text: str) -> list[float]:
        if not self.available or self.provider is None:
            return []
        try:
            return list(self.provider.embedText(text) or [])
        except Exception as error:
            self.available = False
            self.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Embedding provider failed: {error}")
            return []

    def embedBatch(self, texts: list[str]) -> list[list[float]]:
        if not self.available or self.provider is None:
            return [[] for _ in texts]
        try:
            return [list(vector or []) for vector in self.provider.embedBatch(list(texts) or [])]
        except Exception as error:
            self.available = False
            self.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Batch embedding provider failed: {error}")
            return [[] for _ in texts]

    def shutdown(self):
        if self.provider is not None and hasattr(self.provider, "shutdown"):
            self.provider.shutdown()
        if self.store is not None and hasattr(self.store, "close"):
            self.store.close()
        self.available = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "available": bool(self.available),
            "enabled": bool(self.enabled),
            "provider": getattr(self.provider, "providerName", "unknown") if self.provider else "unavailable",
            "model": getattr(self.provider, "modelName", "") if self.provider else "",
            "indexedCount": int(self._indexedCount),
            "lastIndexAt": self.lastIndexAt,
            "lastSearchText": self.lastSearchText,
            "lastError": self.lastError,
            "store": self.store.snapshot() if self.store is not None else {},
            "providerMetadata": self.provider.metadata() if self.provider is not None and hasattr(self.provider, "metadata") else {},
            "failedCount": self._failedCount,
        }

    def _buildProvider(self, config):
        preferred = str(self._getConfigValue(config, "semanticMemory.embeddingProvider", self._getConfigValue(config, "memory.semantic.provider", "gemini")) or "gemini").strip().lower()
        model = str(self._getConfigValue(config, "semanticMemory.embeddingModel", self._getConfigValue(config, "memory.semantic.model", "text-embedding-004")) or "text-embedding-004")
        dimensions = self._getConfigValue(config, "semanticMemory.embeddingDimensions", self._getConfigValue(config, "memory.semantic.dimensions", None))
        providers = []
        if preferred == "gemini":
            providers.extend([GeminiEmbeddingProvider(self.context, model=model, outputDimensionality=dimensions), LocalEmbeddingProvider(self.context)])
        elif preferred == "local":
            providers.extend([LocalEmbeddingProvider(self.context), GeminiEmbeddingProvider(self.context, model=model, outputDimensionality=dimensions)])
        else:
            providers.extend([LocalEmbeddingProvider(self.context), GeminiEmbeddingProvider(self.context, model=model, outputDimensionality=dimensions)])
        for candidate in providers:
            try:
                candidate.initialize()
                if candidate.isAvailable():
                    return candidate
            except Exception as error:
                self.lastError = str(error)
                if self.logger:
                    self.logger.warning(f"Embedding provider initialization failed for {candidate.providerName}: {error}")
        return providers[-1] if providers else None

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        try:
            return eventManager.emit(eventName, payload)
        except Exception:
            return None

    @staticmethod
    def _embeddingText(memory) -> str:
        return " ".join(
            part for part in [
                getattr(memory, "category", ""),
                getattr(memory, "title", ""),
                getattr(memory, "content", ""),
                " ".join(getattr(memory, "tags", []) or []),
                str(getattr(memory, "source", "") or ""),
            ] if part
        )

    @staticmethod
    def _getConfigValue(config, key: str, default=None):
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
