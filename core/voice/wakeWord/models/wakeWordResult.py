"""Wake word prediction result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WakeWordResult:
    """Result of one OpenWakeWord prediction pass."""

    detected: bool = False
    phrase: str = ""
    confidence: float = 0.0
    modelName: str = ""
    predictions: dict[str, float] = field(default_factory=dict)
    predictionTimeMs: float = 0.0
    frameDurationMs: float = 0.0
    errorMessage: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="milliseconds"))

    def asDict(self) -> dict[str, Any]:
        """Return a serializable representation for logging and UI state."""

        return {
            "detected": bool(self.detected),
            "phrase": self.phrase,
            "confidence": float(self.confidence),
            "modelName": self.modelName,
            "predictions": dict(self.predictions),
            "predictionTimeMs": float(self.predictionTimeMs),
            "frameDurationMs": float(self.frameDurationMs),
            "errorMessage": self.errorMessage,
            "timestamp": self.timestamp,
        }
