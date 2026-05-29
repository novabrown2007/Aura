"""Active conversational entity model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActiveEntity:
    """A short-term entity that follow-up turns may refer to."""

    name: str
    entityType: str = ""
    topic: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "conversation"
    createdAt: float = 0.0
    updatedAt: float = 0.0

    def asDict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "entityType": self.entityType,
            "topic": self.topic,
            "attributes": dict(self.attributes),
            "confidence": self.confidence,
            "source": self.source,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

