"""Humor injection model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HumorResponse:
    """A safe optional humorous aside."""

    text: str = ""
    applied: bool = False
    reason: str = ""

    def asDict(self) -> dict:
        return {"text": self.text, "applied": self.applied, "reason": self.reason}

