"""Tracked speech segment produced by VAD endpoint detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class SpeechSegment:
    """Timing and confidence summary for a detected utterance."""

    startedAt: float = field(default_factory=time)
    endedAt: float | None = None
    speechStartedAt: float | None = None
    speechEndedAt: float | None = None
    silenceStartedAt: float | None = None
    confidenceValues: list[float] = field(default_factory=list)
    finalizedReason: str = ""

    @property
    def recordingDuration(self) -> float:
        """Return total active recording duration in seconds."""

        end = self.endedAt if self.endedAt is not None else time()
        return max(0.0, float(end) - float(self.startedAt))

    @property
    def speechDuration(self) -> float:
        """Return detected speech duration in seconds."""

        if self.speechStartedAt is None:
            return 0.0
        end = self.speechEndedAt if self.speechEndedAt is not None else time()
        return max(0.0, float(end) - float(self.speechStartedAt))

    @property
    def silenceDuration(self) -> float:
        """Return current or final trailing silence duration in seconds."""

        if self.silenceStartedAt is None:
            return 0.0
        end = self.endedAt if self.endedAt is not None else time()
        return max(0.0, float(end) - float(self.silenceStartedAt))

    @property
    def averageConfidence(self) -> float:
        """Return the mean speech confidence observed for this segment."""

        if not self.confidenceValues:
            return 0.0
        return sum(self.confidenceValues) / float(len(self.confidenceValues))

    @property
    def peakConfidence(self) -> float:
        """Return the highest speech confidence observed for this segment."""

        return max(self.confidenceValues) if self.confidenceValues else 0.0

    def finish(self, reason: str = "completed", endedAt: float | None = None):
        """Mark the segment as ended."""

        self.endedAt = endedAt if endedAt is not None else time()
        self.finalizedReason = str(reason or "completed")
        if self.speechEndedAt is None:
            self.speechEndedAt = self.endedAt
        return self

    def asDict(self) -> dict:
        """Return a serializable segment snapshot."""

        return {
            "startedAt": self.startedAt,
            "endedAt": self.endedAt,
            "speechStartedAt": self.speechStartedAt,
            "speechEndedAt": self.speechEndedAt,
            "silenceStartedAt": self.silenceStartedAt,
            "recordingDuration": self.recordingDuration,
            "speechDuration": self.speechDuration,
            "silenceDuration": self.silenceDuration,
            "averageConfidence": self.averageConfidence,
            "peakConfidence": self.peakConfidence,
            "finalizedReason": self.finalizedReason,
        }

