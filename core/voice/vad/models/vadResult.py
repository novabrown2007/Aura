"""Realtime VAD detector result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class VADResult:
    """One speech probability result for an audio frame."""

    isSpeech: bool = False
    confidence: float = 0.0
    threshold: float = 0.5
    timestamp: float = field(default_factory=time)
    backend: str = ""
    errorMessage: str = ""

    def asDict(self) -> dict:
        """Return a serializable result for events and developer UI."""

        return {
            "isSpeech": bool(self.isSpeech),
            "confidence": float(self.confidence),
            "threshold": float(self.threshold),
            "timestamp": float(self.timestamp),
            "backend": str(self.backend),
            "errorMessage": str(self.errorMessage or ""),
        }

