"""Top-level voice activity coordinator for Aura."""

from __future__ import annotations

from threading import RLock

from core.voice.vad.configuration import VADConfig
from core.voice.vad.events import VADEvents
from core.voice.vad.models import VADState
from core.voice.vad.speechStateManager import SpeechStateManager
from core.voice.vad.vadDetector import VADDetector
from core.voice.vad.vadSession import VADSession


class VADManager:
    """Coordinate VAD lifecycle, speech state, and recording finalization."""

    def __init__(self, context=None, config: VADConfig | None = None, detector: VADDetector | None = None):
        self.context = context
        self.config = config or VADConfig.fromContext(context)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Voice.VAD") if logger else None
        self.detector = detector or VADDetector(context, self.config)
        self.stateManager = SpeechStateManager(self.logger)
        self.activeSession: VADSession | None = None
        self.lastSession: VADSession | None = None
        self.lastError = ""
        self._lock = RLock()

        if self.context is not None:
            self.context.vadManager = self

        if self.logger:
            self.logger.info(
                "VAD manager created "
                f"(enabled={self.config.vadEnabled}, silence={self.config.vadSilenceThresholdSeconds:.2f}s, "
                f"speechThreshold={self.config.vadSpeechThreshold:.2f})."
            )

    @property
    def enabled(self) -> bool:
        """Return whether VAD endpoint detection is enabled."""

        return bool(self.config.vadEnabled)

    def startSession(self, source: str = "voice") -> VADSession | None:
        """Start a VAD session for the current microphone capture."""

        if not self.enabled:
            return None
        with self._lock:
            self.detector.initialize()
            self.detector.reset()
            self.stateManager.reset("new session")
            self.stateManager.transitionTo(VADState.LISTENING, "capture started")
            self.activeSession = VADSession(self.config, self.detector, self.stateManager, source=source)
            self.lastSession = self.activeSession
            self._emit(VADEvents.STARTED, self._payload(self.activeSession))
            return self.activeSession

    def processFrame(self, audioFrame, sampleRate: int | None = None):
        """Process one recorder frame and emit state events."""

        session = self.activeSession
        if session is None or not self.enabled:
            return None
        try:
            update = session.processFrame(audioFrame, sampleRate=sampleRate)
            if update.get("ignored"):
                return update
            result = update["result"]
            if result.errorMessage:
                self._emit(VADEvents.ERROR, self._payload(session, {"errorMessage": result.errorMessage}))
            if update.get("changedToSpeech"):
                self._debug(f"Speech detected confidence={result.confidence:.3f}")
                self._emit(VADEvents.SPEECH_DETECTED, self._payload(session))
            if update.get("changedToSilence"):
                self._debug(f"Silence detected after {update.get('speechDuration', 0.0):.3f}s speech.")
                self._emit(VADEvents.SILENCE_DETECTED, self._payload(session))
            if update.get("endpointReached"):
                reason = str(update.get("endpointReason") or "completed")
                eventName = VADEvents.TIMEOUT if reason == "timeout" else VADEvents.SPEECH_COMPLETED
                self.stateManager.transitionTo(VADState.FINALIZING, reason)
                self._emit(eventName, self._payload(session, {"reason": reason}))
                self._emit(VADEvents.FINALIZING, self._payload(session, {"reason": reason}))
            return update
        except Exception as error:
            self.lastError = str(error)
            self.stateManager.reset("error")
            self._emit(VADEvents.ERROR, {"errorMessage": str(error)})
            if self.logger:
                self.logger.error(f"VAD frame processing failed: {error}")
            return None

    def waitForCompletion(self, timeoutSeconds: float | None = None) -> bool:
        """Wait for endpoint detection without blocking forever."""

        session = self.activeSession
        if session is None:
            return False
        timeout = timeoutSeconds
        if timeout is None:
            timeout = max(0.1, float(self.config.vadMaxRecordingDuration) + float(self.config.vadSilenceThresholdSeconds))
        return bool(session.completed.wait(float(timeout)))

    def finalizeSession(self, reason: str = "manual"):
        """Finalize active VAD state before the existing STT pipeline runs."""

        with self._lock:
            session = self.activeSession
            if session is None:
                return None
            if not session.completed.is_set():
                session.finalize(reason=reason)
                self.stateManager.transitionTo(VADState.FINALIZING, reason)
                self._emit(VADEvents.FINALIZING, self._payload(session, {"reason": reason}))
            self.stateManager.transitionTo(VADState.PROCESSING, "stt processing")
            self.activeSession = None
            return session

    def cancelSession(self, reason: str = "cancelled") -> bool:
        """Cancel active VAD tracking and return to idle."""

        with self._lock:
            session = self.activeSession
            if session is None:
                self.stateManager.reset(reason)
                return False
            session.cancel(reason=reason)
            self.activeSession = None
            self.stateManager.reset(reason)
            self._emit(VADEvents.ERROR, self._payload(session, {"errorMessage": reason, "cancelled": True}))
            return True

    def markProcessingComplete(self):
        """Reset VAD state after STT has completed."""

        self.stateManager.reset("processing complete")

    def snapshot(self) -> dict:
        """Return current VAD diagnostics for developer UI."""

        session = self.activeSession or self.lastSession
        snapshot = {
            "available": True,
            "enabled": self.enabled,
            "state": self.stateManager.snapshot()["state"],
            "config": {
                "silenceThresholdSeconds": self.config.vadSilenceThresholdSeconds,
                "speechThreshold": self.config.vadSpeechThreshold,
                "minSpeechDuration": self.config.vadMinSpeechDuration,
                "maxRecordingDuration": self.config.vadMaxRecordingDuration,
                "debugLogging": self.config.vadDebugLogging,
            },
            "detector": self.detector.snapshot(),
            "lastError": self.lastError,
        }
        if session is not None:
            sessionSnapshot = session.snapshot()
            silence = sessionSnapshot.get("silence", {})
            segment = silence.get("segment", {})
            lastResult = sessionSnapshot.get("lastResult", {})
            snapshot.update(
                {
                    "session": sessionSnapshot,
                    "source": sessionSnapshot.get("source", ""),
                    "active": bool(sessionSnapshot.get("active")),
                    "speechDetected": bool(silence.get("hasSpeech")),
                    "silenceDetected": bool(segment.get("silenceDuration", 0.0) > 0),
                    "recordingDuration": float(segment.get("recordingDuration") or 0.0),
                    "speechDuration": float(segment.get("speechDuration") or 0.0),
                    "silenceDuration": float(segment.get("silenceDuration") or 0.0),
                    "confidence": float(lastResult.get("confidence") or 0.0),
                    "backend": str(lastResult.get("backend") or self.detector.backend or ""),
                }
            )
        return snapshot

    def _payload(self, session: VADSession | None, extra: dict | None = None) -> dict:
        payload = self.snapshot() if session is not None else {"available": True, "enabled": self.enabled}
        if extra:
            payload.update(extra)
        return payload

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"VAD event emission failed for {eventName}: {error}")

    def _debug(self, message: str):
        if self.config.vadDebugLogging and self.logger:
            self.logger.debug(message)

