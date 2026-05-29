"""Semantic memory retrieval result model."""

from __future__ import annotations

from dataclasses import dataclass

from modules.llm.memory.models.memory import Memory


@dataclass
class SemanticMemoryResult:
    """One retrieved memory with explainable semantic ranking data."""

    memory: Memory
    similarity: float
    relevanceScore: float
    matchedBy: str
    explanation: str
