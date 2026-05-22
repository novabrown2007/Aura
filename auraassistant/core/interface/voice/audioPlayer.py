"""Local WAV playback support for Aura voice output."""

from __future__ import annotations

import time
import wave
from pathlib import Path
from threading import Lock


class AudioPlayer:
    """Play generated local WAV files without a heavyweight media stack."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Voice.AudioPlayer") if context and getattr(context, "logger", None) else None
        self._lock = Lock()
        self._simpleaudio = None
        self._playObject = None
        self._isPlaying = False
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

        with self._lock:
            try:
                start = time.perf_counter()
                self._ensureDependency()
                self._isPlaying = True
                if self.logger:
                    self.logger.info(f"Playing voice audio: {path}")

                if self._simpleaudio is not None:
                    waveObject = self._simpleaudio.WaveObject.from_wave_file(str(path))
                    self._playObject = waveObject.play()
                    self._playObject.wait_done()
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
                self._isPlaying = False
                self._playObject = None

    def stopAudio(self):
        """Stop any active playback request."""

        with self._lock:
            if self._playObject is not None:
                try:
                    self._playObject.stop()
                except Exception as error:
                    self.lastError = str(error)
                    if self.logger:
                        self.logger.warning(f"Failed to stop voice playback: {error}")
                finally:
                    self._playObject = None
            self._isPlaying = False

    def isPlaying(self):
        """Return whether audio is currently playing."""

        return bool(self._isPlaying)

    def _ensureDependency(self):
        """Load the preferred playback backend once."""

        if self._simpleaudio is not None:
            return
        try:
            import simpleaudio as simpleaudio_module
        except Exception:
            self._simpleaudio = None
            return
        self._simpleaudio = simpleaudio_module

    def _playWithWinsound(self, path: Path):
        """Fallback playback for Windows when simpleaudio is unavailable."""

        try:
            import winsound
        except Exception as error:
            raise RuntimeError(f"No supported playback backend is available: {error}") from error

        flags = winsound.SND_FILENAME | winsound.SND_SYNC
        winsound.PlaySound(str(path), flags)
