"""Local WAV playback support for Aura voice output."""

from __future__ import annotations

import time
import wave
from pathlib import Path
from threading import Event, Lock


class AudioPlayer:
    """Play generated local WAV files without a heavyweight media stack."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Voice.AudioPlayer") if context and getattr(context, "logger", None) else None
        self._lock = Lock()
        self._sounddevice = None
        self._numpy = None
        self._isPlaying = False
        self._cancelEvent = Event()
        self.lastError = ""

    def playAudio(self, audioPath: str):
        """Play a WAV file synchronously and return the playback duration."""

        path = Path(str(audioPath or "")).expanduser()
        if not path.exists():
            message = f"Audio file not found: {path}"
            self.lastError = message
            if self.logger:
                self.logger.error(message)
            return 0.0

        try:
            start = time.perf_counter()
            self._ensureDependency()
            with self._lock:
                self._cancelEvent.clear()
                self._isPlaying = True
            self._registerPlaybackOperation(str(path))
            if self.logger:
                self.logger.info(f"Playing voice audio: {path}")

            if self._sounddevice is not None and self._numpy is not None:
                self._playWithSounddevice(path)
            else:
                self._playWithWinsound(path)

            duration = time.perf_counter() - start
            if self.logger:
                self.logger.info(f"Playback finished in {duration:.3f}s")
            return duration
        except Exception as error:
            self.lastError = str(error)
            if self.logger:
                self.logger.error(f"Audio playback failed: {error}")
            return 0.0
        finally:
            with self._lock:
                self._isPlaying = False
            self._completePlaybackOperation()

    def stopAudio(self):
        """Stop any active playback request."""

        with self._lock:
            self._cancelEvent.set()
            self._isPlaying = False
        if self._sounddevice is not None:
            try:
                self._sounddevice.stop()
            except Exception as error:
                self.lastError = str(error)
                if self.logger:
                    self.logger.warning(f"Failed to stop voice playback: {error}")
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def isPlaying(self):
        """Return whether audio is currently playing."""

        return bool(self._isPlaying)

    def _ensureDependency(self):
        """Retained for compatibility with older callers."""

        if self._sounddevice is not None and self._numpy is not None:
            return
        try:
            import numpy as numpy_module
            import sounddevice as sounddevice_module
        except Exception:
            self._sounddevice = None
            self._numpy = None
            return
        self._sounddevice = sounddevice_module
        self._numpy = numpy_module

    def _playWithSounddevice(self, path: Path):
        """Play WAV audio through the shared sounddevice dependency."""

        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frames = handle.readframes(handle.getnframes())

        if sample_width == 1:
            dtype = self._numpy.uint8
        elif sample_width == 2:
            dtype = self._numpy.int16
        elif sample_width == 4:
            dtype = self._numpy.int32
        else:
            raise RuntimeError(f"Unsupported WAV sample width: {sample_width}")

        audio = self._numpy.frombuffer(frames, dtype=dtype)
        if channels > 1:
            audio = audio.reshape(-1, channels)

        self._sounddevice.play(audio, sample_rate)
        self._sounddevice.wait()

    def _playWithWinsound(self, path: Path):
        """Fallback playback for Windows when sounddevice is unavailable."""

        try:
            import winsound
        except Exception as error:
            raise RuntimeError(f"No supported playback backend is available: {error}") from error

        flags = winsound.SND_FILENAME | winsound.SND_SYNC
        winsound.PlaySound(str(path), flags)

    def _registerPlaybackOperation(self, path: str):
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is None:
            return
        try:
            registry.registerOperation(
                "tts.playback",
                "voice",
                "playback",
                cancelHandler=lambda _context: self.stopAudio(),
                metadata={"path": path},
            )
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Failed to register voice playback interruption operation: {error}")

    def _completePlaybackOperation(self):
        registry = getattr(self.context, "interruptionRegistry", None)
        if registry is None:
            return
        try:
            registry.completeOperation("tts.playback")
        except Exception:
            pass
