"""One active VAD-controlled recording session."""

from __future__ import annotations

from threading import Event, RLock
from time import time
from uuid import uuid4

from core.voice.vad.configuration import VADConfig
from core.voice.vad.models import VADResult, VADState
from core.voice.vad.silenceTracker import SilenceTracker
from core.voice.vad.speechStateManager import SpeechStateManager


class VADSession:
    """Track one voice turn until speech endpoint or timeout."""

    def __init__(self, config: VADConfig, detector, stateManager: SpeechStateManager, source: str = "voice"):
        self.config = config
        self.detector = detector
        self.stateManager = stateManager
        self.source = str(source or "voice")
        self.sessionId = uuid4().hex
        self.startedAt = time()
        self.completedAt: float | None = None
        self.cancelled = False
        self.completed = Event()
        self.silenceTracker = SilenceTracker(config)
        self.lastResult = VADResult(threshold=config.vadSpeechThreshold)
        self._lock = RLock()

    def processFrame(self, audioFrame, sampleRate: int | None = None) -> dict:
        """Analyze one frame and update session timing."""

        with self._lock:
            if self.cancelled or self.completed.is_set():
                return {"ignored": True, "endpointReached": self.completed.is_set()}
            result = self.detector.detect(audioFrame, sampleRate=sampleRate)
            self.lastResult = result
            update = self.silenceTracker.update(result)
            if result.isSpeech:
                self.stateManager.transitionTo(VADState.SPEAKING, "speech detected")
            elif self.silenceTracker.hasSpeech:
                self.stateManager.transitionTo(VADState.SILENCE_PENDING, "silence detected")
            if update["endpointReached"]:
                self.completedAt = time()
                self.completed.set()
            update["result"] = result
            update["session"] = self
            return update

    def finalize(self, reason: str = "manual"):
        """Mark this session as ready for the existing STT pipeline."""

        with self._lock:
            if self.completedAt is None:
                self.completedAt = time()
            self.silenceTracker.segment.finish(reason=reason, endedAt=self.completedAt)
            self.completed.set()

    def cancel(self, reason: str = "cancelled"):
        """Cancel the active recording session."""

        with self._lock:
            self.cancelled = True
            self.finalize(reason=reason)

    def snapshot(self) -> dict:
        """Return a serializable session snapshot."""

        with self._lock:
            return {
                "sessionId": self.sessionId,
                "source": self.source,
                "startedAt": self.startedAt,
                "completedAt": self.completedAt,
                "active": not self.completed.is_set() and not self.cancelled,
                "completed": self.completed.is_set(),
                "cancelled": self.cancelled,
                "lastResult": self.lastResult.asDict(),
                "silence": self.silenceTracker.snapshot(),
            }
