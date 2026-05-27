"""Microphone audio stream for OpenWakeWord inference."""

from __future__ import annotations

from queue import Empty, Queue
from threading import Lock
from typing import Any


class WakeWordAudioStream:
    """Read low-latency 16-bit 16 kHz PCM frames from the microphone."""

    def __init__(
        self,
        context=None,
        sampleRate: int = 16000,
        frameDurationMs: int = 80,
        microphoneDevice: str | int | None = None,
        queueSize: int = 8,
    ):
        self.context = context
        self.sampleRate = int(sampleRate)
        self.frameDurationMs = int(frameDurationMs)
        self.microphoneDevice = microphoneDevice
        self.channels = 1
        self.blockSize = max(1, int(self.sampleRate * (self.frameDurationMs / 1000.0)))
        self.logger = context.logger.getChild("Voice.WakeWord.AudioStream") if context and getattr(context, "logger", None) else None
        self._sounddevice = None
        self._numpy = None
        self._stream = None
        self._queue: Queue[Any] = Queue(maxsize=max(1, int(queueSize)))
        self._lock = Lock()
        self._active = False
        self.lastError = ""
        self.lastStatus = ""
        self.framesDropped = 0

    def start(self) -> bool:
        """Open and start the microphone stream."""

        with self._lock:
            if self._active:
                return True
            try:
                self._ensureDependencies()
                self._clearQueue()
                self._stream = self._sounddevice.InputStream(
                    samplerate=self.sampleRate,
                    channels=self.channels,
                    dtype="int16",
                    blocksize=self.blockSize,
                    device=self.microphoneDevice,
                    callback=self._onAudioFrame,
                )
                self._stream.start()
                self._active = True
                self.lastError = ""
                if self.logger:
                    self.logger.info(f"Wake word microphone stream started at {self.sampleRate}Hz, blockSize={self.blockSize}.")
                return True
            except Exception as error:
                self.lastError = str(error)
                self._cleanupStream()
                if self.logger:
                    self.logger.error(f"Wake word microphone stream failed to start: {error}")
                return False

    def stop(self):
        """Stop and close the microphone stream."""

        with self._lock:
            self._cleanupStream()
            self._active = False
            self._clearQueue()
            if self.logger:
                self.logger.info("Wake word microphone stream stopped.")

    def readFrame(self, timeout: float = 0.25):
        """Return the next PCM int16 frame, or None when no audio is available."""

        if not self._active:
            return None
        try:
            return self._queue.get(timeout=float(timeout))
        except Empty:
            return None

    def isActive(self) -> bool:
        """Return whether the stream is currently active."""

        return bool(self._active)

    def snapshot(self) -> dict:
        """Return lightweight microphone state for diagnostics."""

        return {
            "active": self.isActive(),
            "sampleRate": self.sampleRate,
            "frameDurationMs": self.frameDurationMs,
            "blockSize": self.blockSize,
            "device": self.microphoneDevice,
            "queuedFrames": self._queue.qsize(),
            "framesDropped": self.framesDropped,
            "lastError": self.lastError,
            "lastStatus": self.lastStatus,
        }

    def _onAudioFrame(self, indata: Any, frames: int, timeInfo: Any, status: Any):
        """Copy microphone frames into a bounded queue without growing memory."""

        if status:
            self.lastStatus = str(status)
            if self.logger:
                self.logger.debug(f"Wake word microphone status: {status}")
        try:
            np = self._numpy
            frame = np.copy(indata).reshape(-1).astype(np.int16, copy=False) if np is not None else indata
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except Empty:
                    pass
                self.framesDropped += 1
            self._queue.put_nowait(frame)
        except Exception as error:
            self.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Wake word audio frame dropped: {error}")

    def _ensureDependencies(self):
        if self._sounddevice is None:
            try:
                import sounddevice as sounddeviceModule
            except Exception as error:
                raise RuntimeError(f"sounddevice is unavailable: {error}") from error
            self._sounddevice = sounddeviceModule
        if self._numpy is None:
            try:
                import numpy as numpyModule
            except Exception as error:
                raise RuntimeError(f"numpy is unavailable: {error}") from error
            self._numpy = numpyModule

    def _cleanupStream(self):
        if self._stream is None:
            return
        try:
            self._stream.stop()
        finally:
            try:
                self._stream.close()
            finally:
                self._stream = None

    def _clearQueue(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break
