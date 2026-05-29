"""Semantic retrieval query model for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SemanticMemoryQuery:
    """Query parameters for meaning-based memory retrieval."""

    queryText: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    maxResults: int = 5
    minimumSimilarity: float = 0.65
    includeArchived: bool = False
    recencyWeight: float = 0.2
    importanceWeight: float = 0.2
    similarityWeight: float = 0.6
