"""Push-to-talk microphone capture for Aura."""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from threading import Lock
from typing import Any


class VoiceRecorder:
    """Record mono 16kHz audio into a temporary WAV file."""

    def __init__(self, context=None, sampleRate: int = 16000, channels: int = 1, tempDirectory: str | None = None):
        self.context = context
        self.sampleRate = int(sampleRate)
        self.channels = int(channels)
        self.blockSize = max(160, int(self.sampleRate * 0.032))
        self.tempDirectory = str(tempDirectory or "").strip()
        self.logger = context.logger.getChild("Voice.Recorder") if context and getattr(context, "logger", None) else None
        self._lock = Lock()
        self._sounddevice = None
        self._numpy = None
        self._stream = None
        self._frames: list[Any] = []
        self._tempPath: Path | None = None
        self._active = False
        self._audioChunkHandler = None
        self.lastError = ""

    def startRecording(self):
        """Start a push-to-talk recording session."""

        with self._lock:
            if self._active:
                return True

            try:
                self._ensureDependencies()
                self._frames = []
                self._tempPath = None
                self._stream = self._createInputStream()
                self._stream.start()
                self._active = True
                if self.logger:
                    self.logger.info(f"Voice capture started at {self.sampleRate}Hz mono.")
                return True
            except Exception as error:
                self.lastError = str(error)
                self._cleanupStream()
                if self.logger:
                    self.logger.error(f"Voice capture could not start: {error}")
                return False

    def stopRecording(self):
        """Stop the current push-to-talk recording session."""

        with self._lock:
            if not self._active:
                return False

            try:
                self._cleanupStream()
                self._active = False
                if self.logger:
                    self.logger.info("Voice capture stopped.")
                return True
            except Exception as error:
                self.lastError = str(error)
                if self.logger:
                    self.logger.error(f"Voice capture could not stop cleanly: {error}")
                return False

    def saveRecording(self):
        """Persist the captured audio into a temporary WAV file."""

        with self._lock:
            if not self._frames:
                self.lastError = "No audio was captured."
                if self.logger:
                    self.logger.warning("No voice audio captured.")
                return None

            try:
                np = self._numpy
                if np is None:
                    self._ensureDependencies()
                    np = self._numpy
                if np is None:
                    raise RuntimeError("numpy is unavailable.")
                audio = np.concatenate(self._frames, axis=0)
                if audio.ndim > 1 and audio.shape[1] > 1:
                    audio = audio[:, 0:1]
                audio = np.asarray(audio, dtype=np.int16)
                if audio.ndim > 1:
                    audio = audio.reshape(-1)

                tempDir = Path(self.tempDirectory).expanduser() if self.tempDirectory else None
                if tempDir is not None:
                    tempDir.mkdir(parents=True, exist_ok=True)
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".wav",
                    dir=str(tempDir) if tempDir is not None else None,
                )
                temp_file.close()
                path = Path(temp_file.name)

                with wave.open(str(path), "wb") as handle:
                    handle.setnchannels(self.channels)
                    handle.setsampwidth(2)
                    handle.setframerate(self.sampleRate)
                    handle.writeframes(audio.tobytes())

                self._tempPath = path
                if self.logger:
                    self.logger.info(f"Voice recording saved to {path}")
                return str(path)
            except Exception as error:
                self.lastError = str(error)
                if self.logger:
                    self.logger.error(f"Voice recording could not be saved: {error}")
                return None

    def cleanup(self):
        """Remove any saved temp audio and reset the capture buffer."""

        with self._lock:
            self._cleanupStream()
            if self._tempPath is not None:
                try:
                    self._tempPath.unlink(missing_ok=True)
                except Exception as error:
                    if self.logger:
                        self.logger.warning(f"Failed to remove temporary voice file: {error}")
            self._tempPath = None
            self._frames = []

    def isRecording(self) -> bool:
        """Return whether the recorder currently has an active input stream."""

        return bool(self._active)

    def setAudioChunkHandler(self, handler):
        """Install an optional observer for realtime audio chunks."""

        with self._lock:
            self._audioChunkHandler = handler

    def _onAudioChunk(self, indata: Any, frames: int, time_info: Any, status: Any):
        """Collect audio chunks from the microphone callback."""

        if status and self.logger:
            self.logger.debug(f"Voice input status: {status}")
        np = self._numpy
        if np is None:
            self._frames.append(indata)
            chunk = indata
        else:
            chunk = np.copy(indata)
            self._frames.append(chunk)
        handler = self._audioChunkHandler
        if handler is None:
            return
        try:
            handler(chunk, self.sampleRate)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Voice audio chunk observer failed: {error}")

    def _ensureDependencies(self):
        """Load optional audio capture dependencies once."""

        if self._sounddevice is None:
            try:
                import sounddevice as sounddevice_module
            except Exception as error:
                raise RuntimeError(f"sounddevice is unavailable: {error}") from error
            self._sounddevice = sounddevice_module

        if self._numpy is None:
            try:
                import numpy as numpy_module
            except Exception as error:
                raise RuntimeError(f"numpy is unavailable: {error}") from error

    def _createInputStream(self):
        """Create a low-latency microphone stream, with legacy fake compatibility."""

        kwargs = {
            "samplerate": self.sampleRate,
            "channels": self.channels,
            "dtype": "int16",
            "callback": self._onAudioChunk,
            "blocksize": self.blockSize,
        }
        try:
            return self._sounddevice.InputStream(**kwargs)
        except TypeError:
            kwargs.pop("blocksize", None)
            return self._sounddevice.InputStream(**kwargs)
            self._numpy = numpy_module

    def _cleanupStream(self):
        """Stop and close any active audio stream."""

        if self._stream is None:
            return
        try:
            self._stream.stop()
        finally:
            try:
                self._stream.close()
            finally:
                self._stream = None
