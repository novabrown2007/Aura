"""Memory model used by Aura's structured long-term memory layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from modules.llm.memory.models.memoryCategory import MemoryCategory


def utcNow() -> str:
    """Return a stable UTC timestamp for persisted memory rows."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Memory:
    """One durable, categorized assistant memory."""

    category: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    source: str = "manual"
    sessionId: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    memoryId: str = field(default_factory=lambda: uuid4().hex)
    createdAt: str = field(default_factory=utcNow)
    updatedAt: str = field(default_factory=utcNow)

    def __post_init__(self):
        """Normalize persisted fields after construction."""

        self.category = MemoryCategory.normalize(self.category)
        self.title = str(self.title or "").strip()
        self.content = str(self.content or "").strip()
        self.tags = sorted({str(tag).strip().lower() for tag in self.tags if str(tag).strip()})
        self.importance = max(0.0, min(1.0, float(self.importance)))
        self.source = str(self.source or "manual").strip()
        self.sessionId = str(self.sessionId or "").strip()
        self.metadata = dict(self.metadata or {})

    def asDict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return {
            "memoryId": self.memoryId,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "tags": list(self.tags),
            "importance": self.importance,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "source": self.source,
            "sessionId": self.sessionId,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, data: dict[str, Any]) -> "Memory":
        """Build a Memory from storage or API data."""

        return cls(
            memoryId=str(data.get("memoryId") or data.get("memory_id") or uuid4().hex),
            category=str(data.get("category") or ""),
            title=str(data.get("title") or ""),
            content=str(data.get("content") or ""),
            tags=list(data.get("tags") or []),
            importance=float(data.get("importance", 0.5)),
            createdAt=str(data.get("createdAt") or data.get("created_at") or utcNow()),
            updatedAt=str(data.get("updatedAt") or data.get("updated_at") or utcNow()),
            source=str(data.get("source") or "manual"),
            sessionId=str(data.get("sessionId") or data.get("session_id") or ""),
            metadata=dict(data.get("metadata") or {}),
        )

