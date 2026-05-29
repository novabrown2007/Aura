"""Silence endpoint tracking for VAD-controlled recordings."""

from __future__ import annotations

from time import time

from core.voice.vad.configuration import VADConfig
from core.voice.vad.models import SpeechSegment, VADResult


class SilenceTracker:
    """Detect utterance endpoints from speech and silence timing."""

    def __init__(self, config: VADConfig | None = None, clock=None):
        self.config = config or VADConfig()
        self.clock = clock or time
        self.segment = SpeechSegment(startedAt=self.clock())
        self.hasSpeech = False
        self.endpointReached = False
        self.endpointReason = ""
        self.lastResult: VADResult | None = None

    def reset(self):
        """Reset timing for a new recording session."""

        self.segment = SpeechSegment(startedAt=self.clock())
        self.hasSpeech = False
        self.endpointReached = False
        self.endpointReason = ""
        self.lastResult = None

    def update(self, result: VADResult) -> dict:
        """Update speech/silence timing and return endpoint status."""

        now = float(result.timestamp if result.timestamp is not None else self.clock())
        if self.lastResult is None and now < self.segment.startedAt:
            self.segment.startedAt = now
        self.lastResult = result
        changedToSpeech = False
        changedToSilence = False

        if result.isSpeech:
            if not self.hasSpeech:
                self.hasSpeech = True
                self.segment.speechStartedAt = now
                changedToSpeech = True
            if self.segment.silenceStartedAt is not None:
                changedToSpeech = True
            self.segment.silenceStartedAt = None
            self.segment.speechEndedAt = now
            self.segment.confidenceValues.append(float(result.confidence))
        else:
            if self.hasSpeech and self.segment.silenceStartedAt is None:
                self.segment.silenceStartedAt = now
                changedToSilence = True

        reason = self._endpointReason(now)
        if reason:
            self.endpointReached = True
            self.endpointReason = reason
            self.segment.finish(reason=reason, endedAt=now)

        return {
            "changedToSpeech": changedToSpeech,
            "changedToSilence": changedToSilence,
            "endpointReached": self.endpointReached,
            "endpointReason": self.endpointReason,
            "segment": self.segment,
            "speechDuration": self.segment.speechDuration,
            "silenceDuration": self.segment.silenceDuration,
            "recordingDuration": self.segment.recordingDuration,
        }

    def _endpointReason(self, now: float) -> str:
        maxDuration = max(0.1, float(self.config.vadMaxRecordingDuration))
        if now - float(self.segment.startedAt) >= maxDuration:
            return "timeout"

        if not self.hasSpeech or self.segment.silenceStartedAt is None:
            return ""

        if self.segment.speechDuration < max(0.0, float(self.config.vadMinSpeechDuration)):
            return ""

        silenceDuration = now - float(self.segment.silenceStartedAt)
        if silenceDuration >= max(0.0, float(self.config.vadSilenceThresholdSeconds)):
            return "silence"
        return ""

    def snapshot(self) -> dict:
        """Return current timing data."""

        result = self.lastResult.asDict() if self.lastResult is not None else {}
        return {
            "hasSpeech": self.hasSpeech,
            "endpointReached": self.endpointReached,
            "endpointReason": self.endpointReason,
            "lastResult": result,
            "segment": self.segment.asDict(),
        }
