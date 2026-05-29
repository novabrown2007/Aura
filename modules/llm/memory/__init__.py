"""LLM-owned memory systems for Aura.

Keep this package lazy so newer assistant-layer memory code can import
legacy submodules without eagerly instantiating the full memory manager.
"""

from __future__ import annotations

__all__ = [
    "ContextualRetriever",
    "EmbeddingProvider",
    "MemoryManager",
    "Memory",
    "MemoryCategory",
    "MemoryQuery",
    "MemorySummary",
    "RetrievalResult",
    "SemanticMemoryStore",
]


def __getattr__(name: str):
    if name == "EmbeddingProvider":
        from modules.llm.memory.embeddingProvider import EmbeddingProvider

        return EmbeddingProvider
    if name == "MemoryManager":
        from modules.llm.memory.memoryManager import MemoryManager

        return MemoryManager
    if name in {"Memory", "MemoryCategory", "MemoryQuery", "MemorySummary"}:
        from modules.llm.memory.models import Memory, MemoryCategory, MemoryQuery, MemorySummary

        return {
            "Memory": Memory,
            "MemoryCategory": MemoryCategory,
            "MemoryQuery": MemoryQuery,
            "MemorySummary": MemorySummary,
        }[name]
    if name == "ContextualRetriever" or name == "RetrievalResult":
        from modules.llm.memory.retrieval import ContextualRetriever, RetrievalResult

        return {"ContextualRetriever": ContextualRetriever, "RetrievalResult": RetrievalResult}[name]
    if name == "SemanticMemoryStore":
        from modules.llm.memory.semanticMemoryStore import SemanticMemoryStore

        return SemanticMemoryStore
    raise AttributeError(name)
