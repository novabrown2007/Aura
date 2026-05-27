"""Wake word event payload model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WakeWordEvent:
    """Serializable wake word event payload for Aura's event bus."""

    phrase: str
    confidence: float = 0.0
    modelName: str = ""
    state: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="milliseconds"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return an event-bus-friendly dictionary."""

        data = {
            "phrase": self.phrase,
            "confidence": float(self.confidence),
            "modelName": self.modelName,
            "state": self.state,
            "timestamp": self.timestamp,
        }
        data.update(dict(self.metadata or {}))
        return data
