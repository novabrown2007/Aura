"""Suggestion model for Aura initiative."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class Suggestion:
    """A lightweight optional suggestion."""

    text: str
    reason: str = ""
    category: str = "general"
    priority: float = 0.5
    createdAt: float = field(default_factory=time)

    def asDict(self) -> dict:
        return {
            "text": self.text,
            "reason": self.reason,
            "category": self.category,
            "priority": self.priority,
            "createdAt": self.createdAt,
        }

