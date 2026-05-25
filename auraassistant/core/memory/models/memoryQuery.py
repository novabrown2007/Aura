"""Query model for deterministic memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryQuery:
    """Structured filters used by retrievers and stores."""

    keywords: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    minImportance: float | None = None
    limit: int | None = None
    sessionId: str = ""
    recentDays: int | None = None

    def normalizedTags(self) -> list[str]:
        """Return normalized tag filters."""

        return [str(tag).strip().lower() for tag in self.tags if str(tag).strip()]

