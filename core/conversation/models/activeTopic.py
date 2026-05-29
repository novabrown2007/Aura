"""Active conversational topic model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ActiveTopic:
    """A short-term topic such as lighting, music, calendar, or email."""

    name: str
    confidence: float = 1.0
    source: str = "conversation"
    createdAt: float = 0.0
    updatedAt: float = 0.0

    def asDict(self) -> dict:
        return {
            "name": self.name,
            "confidence": self.confidence,
            "source": self.source,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

