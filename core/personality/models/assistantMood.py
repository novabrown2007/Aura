"""Bounded assistant style state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AssistantMood:
    """Non-sentient style descriptor for future tone systems."""

    label: str = "neutral"
    energy: float = 0.4

    def asDict(self) -> dict:
        return {"label": self.label, "energy": self.energy}

