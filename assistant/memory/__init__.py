"""Assistant memory layer exports."""

from __future__ import annotations

from assistant.memory.hybridMemoryRetriever import HybridMemoryRetriever
from assistant.memory.injector import MemoryInjector
from assistant.memory.memoryEmbeddingManager import MemoryEmbeddingManager
from assistant.memory.memoryRelevanceScorer import MemoryRelevanceScorer
from assistant.memory.memoryRetriever import MemoryRetriever
from assistant.memory.semanticMemoryIndex import SemanticMemoryIndex
from assistant.memory.semanticMemoryRetriever import SemanticMemoryRetriever
from assistant.memory.storage import SQLiteEmbeddingStore
from modules.llm.memory.embeddingProvider import EmbeddingProvider
from modules.llm.memory.models import Memory, MemoryCategory, MemoryQuery, MemorySummary
from modules.llm.memory.retrieval.contextualRetriever import ContextualRetriever, RetrievalResult
from modules.llm.memory.semanticMemoryStore import SemanticMemoryStore

__all__ = [
    "ContextualRetriever",
    "EmbeddingProvider",
    "HybridMemoryRetriever",
    "Memory",
    "MemoryCategory",
    "MemoryInjector",
    "MemoryManager",
    "MemoryEmbeddingManager",
    "MemoryQuery",
    "MemoryRelevanceScorer",
    "MemoryRetriever",
    "MemorySummary",
    "RetrievalResult",
    "SemanticMemoryIndex",
    "SemanticMemoryRetriever",
    "SemanticMemoryStore",
    "SQLiteEmbeddingStore",
]


def __getattr__(name: str):
    if name == "MemoryManager":
        from assistant.memory.memoryManager import MemoryManager

        return MemoryManager
    raise AttributeError(name)
