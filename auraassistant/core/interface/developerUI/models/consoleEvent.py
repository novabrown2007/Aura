"""Developer console event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def currentTimestamp() -> str:
    """Return a compact local timestamp for UI display."""

    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


@dataclass
class ConsoleEvent:
    """A normalized Aura event for developer UI display."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "eventBus"
    category: str = "general"
    timestamp: str = field(default_factory=currentTimestamp)
    durationMs: float = 0.0
    error: str = ""

    def summary(self, maxCharacters: int = 220) -> str:
        """Return a concise payload summary."""

        if self.error:
            text = f"error={self.error}"
        else:
            parts = []
            for key, value in sorted((self.payload or {}).items()):
                rendered = str(value)
                if len(rendered) > 80:
                    rendered = rendered[:77] + "..."
                parts.append(f"{key}={rendered}")
            text = ", ".join(parts)
        if len(text) > maxCharacters:
            return text[: maxCharacters - 3].rstrip() + "..."
        return text

    def asDict(self) -> dict[str, Any]:
        """Return a serializable event."""

        return {
            "name": self.name,
            "payload": dict(self.payload or {}),
            "source": self.source,
            "category": self.category,
            "timestamp": self.timestamp,
            "durationMs": self.durationMs,
            "error": self.error,
            "summary": self.summary(),
        }

