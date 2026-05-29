"""Pending clarification state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClarificationState:
    """A pending clarification that can be completed by a short reply."""

    active: bool = False
    question: str = ""
    pendingIntent: dict[str, Any] = field(default_factory=dict)
    missingField: str = ""
    createdAt: float = 0.0
    updatedAt: float = 0.0

    def asDict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "question": self.question,
            "pendingIntent": dict(self.pendingIntent),
            "missingField": self.missingField,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

