"""Asynchronous wake word microphone listener."""

from __future__ import annotations

from threading import Event, Lock, Thread, current_thread
from time import perf_counter, sleep
from typing import Callable

from .audio import WakeWordAudioStream
from .configuration import WakeWordConfig
from .models import WakeWordResult
from .wakeWordDetector import WakeWordDetector


class WakeWordListener:
    """Continuously feed microphone PCM frames into the wake word detector."""

    def __init__(
        self,
        context=None,
        detector: WakeWordDetector | None = None,
        audioStream: WakeWordAudioStream | None = None,
        config: WakeWordConfig | None = None,
        onDetected: Callable[[WakeWordResult], None] | None = None,
        onPrediction: Callable[[WakeWordResult], None] | None = None,
        onError: Callable[[str], None] | None = None,
    ):
        self.context = context
        self.config = config or WakeWordConfig.fromContext(context)
        self.detector = detector or WakeWordDetector(context, self.config)
        self.audioStream = audioStream or WakeWordAudioStream(
            context,
            sampleRate=self.config.wakeWordSampleRate,
            frameDurationMs=self.config.wakeWordFrameDurationMs,
            microphoneDevice=self.config.wakeWordMicrophoneDevice,
        )
        self.onDetected = onDetected
        self.onPrediction = onPrediction
        self.onError = onError
        self.logger = context.logger.getChild("Voice.WakeWord.Listener") if context and getattr(context, "logger", None) else None
        self._stopEvent = Event()
        self._pauseEvent = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self.running = False
        self.listening = False
        self.lastLoopTimeMs = 0.0
        self.lastFrameAt = 0.0
        self.errorCount = 0

    def start(self) -> bool:
        """Start the listener thread."""

        with self._lock:
            if self.running:
                self.resume()
                return True
            self._stopEvent.clear()
            self._pauseEvent.clear()
            self._thread = Thread(target=self._run, name="AuraWakeWordListener", daemon=True)
            self._thread.start()
            self.running = True
            if self.logger:
                self.logger.info("Wake word listener thread started.")
            return True

    def pause(self):
        """Pause microphone inference without destroying detector state."""

        self._pauseEvent.set()
        self.listening = False
        self.audioStream.stop()
        if self.logger:
            self.logger.info("Wake word listener paused.")

    def resume(self):
        """Resume microphone inference."""

        self._pauseEvent.clear()
        if self.logger:
            self.logger.info("Wake word listener resumed.")

    def stop(self):
        """Stop the listener thread and release microphone resources."""

        self._stopEvent.set()
        self._pauseEvent.clear()
        self.audioStream.stop()
        thread = self._thread
        if thread is not None and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=2.0)
        self.running = False
        self.listening = False
        if self.logger:
            self.logger.info("Wake word listener stopped.")

    def snapshot(self) -> dict:
        """Return listener diagnostics."""

        return {
            "running": self.running,
            "listening": self.listening,
            "paused": self._pauseEvent.is_set(),
            "lastLoopTimeMs": self.lastLoopTimeMs,
            "lastFrameAt": self.lastFrameAt,
            "errorCount": self.errorCount,
            "audio": self.audioStream.snapshot(),
        }

    def _run(self):
        try:
            self.detector.initialize()
        except Exception as error:
            self._handleError(f"Wake word detector initialization failed: {error}")
            self.running = False
            return

        while not self._stopEvent.is_set():
            if self._pauseEvent.is_set():
                sleep(0.05)
                continue
            if not self.audioStream.isActive():
                if not self.audioStream.start():
                    self._handleError(self.audioStream.lastError or "Wake word microphone stream could not start.")
                    sleep(1.0)
                    continue
                self.listening = True

            started = perf_counter()
            frame = self.audioStream.readFrame(timeout=0.25)
            self.lastLoopTimeMs = (perf_counter() - started) * 1000.0
            if frame is None:
                continue
            self.lastFrameAt = perf_counter()
            result = self.detector.processFrame(frame)
            if result.errorMessage:
                self._handleError(result.errorMessage)
                sleep(0.05)
                continue
            if self.onPrediction is not None:
                self.onPrediction(result)
            if result.detected:
                self.pause()
                if self.onDetected is not None:
                    self.onDetected(result)

        self.audioStream.stop()
        self.running = False
        self.listening = False

    def _handleError(self, message: str):
        self.errorCount += 1
        if self.logger:
            self.logger.error(message)
        if self.onError is not None:
            self.onError(message)
