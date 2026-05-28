"""Top-level local wake word manager for Aura."""

from __future__ import annotations

from threading import Lock, Thread
from time import perf_counter, sleep

from .configuration import WakeWordConfig
from .events import WakeWordEvents
from .models import WakeWordEvent, WakeWordResult
from .wakeWordDetector import WakeWordDetector
from .wakeWordListener import WakeWordListener
from .wakeWordSession import WakeWordSession


class WakeWordManager:
    """Coordinate OpenWakeWord detection, events, cooldown, and voice activation."""

    def __init__(self, context=None, config: WakeWordConfig | None = None):
        self.context = context
        self.config = config or WakeWordConfig.fromContext(context)
        self.logger = context.logger.getChild("Voice.WakeWord") if context and getattr(context, "logger", None) else None
        self.detector = WakeWordDetector(context, self.config)
        self.session = WakeWordSession(context, self.config)
        self.listener = WakeWordListener(
            context,
            detector=self.detector,
            config=self.config,
            onDetected=self.handleWakeWordDetected,
            onPrediction=self._handlePrediction,
            onError=self._emitError,
        )
        self.initialized = False
        self.state = "idle"
        self.lastConfidence = 0.0
        self.lastDetectionLatencyMs = 0.0
        self.lastActivationFrequency = 0.0
        self._lock = Lock()
        self._activationThread: Thread | None = None

        if self.context is not None:
            self.context.wakeWordManager = self

        if self.logger:
            self.logger.info(
                "Wake word manager created "
                f"(enabled={self.config.wakeWordEnabled}, phrase={self.config.wakeWordPhrase}, "
                f"autoStart={self.config.wakeWordAutoStart}, modelPath={self.config.wakeWordModelPath or 'default'})."
            )

    def initialize(self) -> bool:
        """Initialize wake word components and optionally begin passive listening."""

        if self.initialized:
            return True
        if not self.config.wakeWordEnabled:
            self.state = "disabled"
            if self.logger:
                self.logger.info("Wake word detection disabled by configuration.")
            return False
        try:
            self.detector.initialize()
            self.initialized = True
            self.state = "idle"
            if self.logger:
                self.logger.info(
                    "Wake word manager initialized "
                    f"(phrase={self.config.wakeWordPhrase}, autoStart={self.config.wakeWordAutoStart}, "
                    f"captureSeconds={self.config.wakeWordCaptureSeconds})."
                )
                if getattr(self.detector, "fallbackActive", False):
                    self.logger.warning(
                        "Wake word custom model fallback is active. "
                        f"Listening for '{self.detector.activeWakePhrases[0]}' until an Aura wake model is installed."
                    )
            if self.config.wakeWordAutoStart:
                self.startListening()
            return True
        except Exception as error:
            self._emitError(f"Wake word initialization failed: {error}")
            return False

    def startListening(self) -> bool:
        """Begin passive wake word listening."""

        if not self.config.wakeWordEnabled:
            return False
        if not self.initialized:
            if not self.initialize():
                return False
        try:
            started = self.listener.start()
            self.listener.resume()
            self.state = "listening" if started else "idle"
            if started:
                self._emit(
                    WakeWordEvents.LISTENING_STARTED,
                    WakeWordEvent(self.config.wakeWordPhrase, self.lastConfidence, state=self.state).asDict(),
                )
            return bool(started)
        except Exception as error:
            self._emitError(f"Wake word listening could not start: {error}")
            return False

    def stopListening(self):
        """Stop passive wake word listening."""

        try:
            self.listener.stop()
            self.state = "idle"
            self._emit(
                WakeWordEvents.LISTENING_STOPPED,
                WakeWordEvent(self.config.wakeWordPhrase, self.lastConfidence, state=self.state).asDict(),
            )
        except Exception as error:
            self._emitError(f"Wake word listening could not stop cleanly: {error}")

    def handleWakeWordDetected(self, result: WakeWordResult):
        """Handle a positive OpenWakeWord prediction and activate Aura voice."""

        with self._lock:
            if not self.session.beginActivation(result):
                return
            self.state = "activated"
            self.lastConfidence = result.confidence
            self.lastDetectionLatencyMs = result.predictionTimeMs
            self.lastActivationFrequency = self._activationFrequency()
            payload = result.asDict()
            payload.update({"state": self.state, "activationCount": self.session.activationCount})
            self._emit(WakeWordEvents.DETECTED, payload)
            if self.logger:
                self.logger.info(f"Wake word detected: phrase={result.phrase}, confidence={result.confidence:.3f}.")
            self._activationThread = Thread(target=self._runActivatedVoiceLoop, args=(result,), name="AuraWakeWordActivation", daemon=True)
            self._activationThread.start()

    def shutdown(self):
        """Release wake word resources without crashing Aura shutdown."""

        try:
            self.stopListening()
            self.state = "shutdown"
            if self.logger:
                self.logger.info("Wake word manager shutdown complete.")
        except Exception as error:
            self._emitError(f"Wake word shutdown failed: {error}")

    def snapshot(self) -> dict:
        """Return operational state for developer UI integration."""

        return {
            "enabled": self.config.wakeWordEnabled,
            "state": self.state,
            "listening": self.listener.listening,
            "phrase": self.config.wakeWordPhrase,
            "validPhrases": self.config.validWakeWordPhrases(),
            "effectivePhrases": list(getattr(self.detector, "activeWakePhrases", None) or self.config.validWakeWordPhrases()),
            "confidence": self.lastConfidence,
            "lastDetectionLatencyMs": self.lastDetectionLatencyMs,
            "activationFrequency": self.lastActivationFrequency,
            "session": self.session.snapshot(),
            "detector": self.detector.snapshot(),
            "listener": self.listener.snapshot(),
        }

    def _runActivatedVoiceLoop(self, result: WakeWordResult):
        started = perf_counter()
        self.session.startCooldown()
        self._emit(
            WakeWordEvents.COOLDOWN_STARTED,
            {
                "phrase": result.phrase,
                "cooldownSeconds": self.config.wakeWordCooldownSeconds,
                "confidence": result.confidence,
            },
        )
        try:
            self._activateExistingVoicePipeline()
        finally:
            remaining = self.session.cooldownRemainingSeconds()
            if remaining > 0:
                sleep(remaining)
            self.session.finishCooldown()
            self._emit(WakeWordEvents.COOLDOWN_FINISHED, {"phrase": result.phrase})
            self.state = "idle"
            if self.config.wakeWordEnabled:
                self.startListening()
            self.lastDetectionLatencyMs = (perf_counter() - started) * 1000.0

    def _activateExistingVoicePipeline(self):
        """Run one fixed-duration turn through the existing push-to-talk path."""

        pushToTalk = getattr(self.context, "pushToTalkManager", None)
        if pushToTalk is None:
            voiceManager = getattr(self.context, "voiceManager", None)
            pushToTalk = getattr(voiceManager, "pushToTalkManager", None)
        if pushToTalk is None:
            self._emitError("Wake word activation failed: push-to-talk manager is unavailable.")
            return

        originalEnabled = getattr(pushToTalk, "enabled", True)
        try:
            pushToTalk.enabled = True
            if not pushToTalk.startCapture(source="always_active"):
                self._emitError(getattr(pushToTalk.lastResult, "errorMessage", "") or "Wake word voice capture could not start.")
                return
            sleep(max(0.1, float(self.config.wakeWordCaptureSeconds)))
            result = pushToTalk.stopAndProcess()
            if not getattr(result, "success", False):
                self._emitError(getattr(result, "errorMessage", "") or "Wake word voice loop failed.")
            else:
                speech = getattr(result, "speech", None)
                self._emit(
                    WakeWordEvents.VOICE_COMPLETED,
                    {
                        "transcribedText": getattr(result, "transcribedText", ""),
                        "assistantResponse": getattr(result, "assistantResponse", ""),
                        "speechError": getattr(speech, "errorMessage", "") if speech and not getattr(speech, "success", False) else "",
                    },
                )
        except Exception as error:
            self._emitError(f"Wake word voice activation failed: {error}")
        finally:
            pushToTalk.enabled = originalEnabled

    def _handlePrediction(self, result: WakeWordResult):
        self.lastConfidence = result.confidence
        if self.config.wakeWordDebugLogging and self.logger:
            self.logger.debug(f"Wake word confidence={result.confidence:.3f}, predictionTimeMs={result.predictionTimeMs:.2f}.")

    def _activationFrequency(self) -> float:
        activationCount = max(1, self.session.activationCount)
        return float(activationCount)

    def _emitError(self, message: str):
        self.state = "error" if not self.listener.running else self.state
        if self.logger:
            self.logger.error(message)
        self._emit(WakeWordEvents.ERROR, {"errorMessage": str(message), "state": self.state})

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Wake word event emission failed for {eventName}: {error}")
