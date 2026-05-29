"""Embedding record for one structured memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utcNow() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class MemoryEmbedding:
    """Persisted semantic embedding linked to one memory row."""

    embeddingId: str = field(default_factory=lambda: uuid4().hex)
    memoryId: str = ""
    provider: str = ""
    model: str = ""
    vector: list[float] = field(default_factory=list)
    createdAt: str = field(default_factory=utcNow)
    updatedAt: str = field(default_factory=utcNow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "embeddingId": self.embeddingId,
            "memoryId": self.memoryId,
            "provider": self.provider,
            "model": self.model,
            "vector": list(self.vector),
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def fromDict(cls, data: dict[str, Any]) -> "MemoryEmbedding":
        return cls(
            embeddingId=str(data.get("embeddingId") or data.get("embedding_id") or uuid4().hex),
            memoryId=str(data.get("memoryId") or data.get("memory_id") or ""),
            provider=str(data.get("provider") or ""),
            model=str(data.get("model") or ""),
            vector=[float(value) for value in (data.get("vector") or [])],
            createdAt=str(data.get("createdAt") or data.get("created_at") or utcNow()),
            updatedAt=str(data.get("updatedAt") or data.get("updated_at") or utcNow()),
            metadata=dict(data.get("metadata") or {}),
        )
