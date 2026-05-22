"""Local Faster-Whisper transcription support for Aura."""

from __future__ import annotations

import time
import wave
from pathlib import Path
from threading import Lock
from typing import Any

from .models.transcriptionResult import TranscriptionResult


class SpeechToText:
    """Manage one cached Faster-Whisper model and transcribe local audio."""

    def __init__(
        self,
        context=None,
        modelName: str = "small.en",
        device: str = "cpu",
        computeType: str = "int8",
    ):
        self.context = context
        self.modelName = modelName
        self.device = device
        self.computeType = computeType
        self.model = None
        self.initialized = False
        self.lastResult = TranscriptionResult()
        self.lastError = ""
        self._lock = Lock()
        self.logger = context.logger.getChild("Voice.STT") if context and getattr(context, "logger", None) else None

    def initialize(self):
        """Load the Whisper model once and cache it in memory."""

        if self.model is not None:
            return self.model

        with self._lock:
            if self.model is not None:
                return self.model

            start = time.perf_counter()
            try:
                from faster_whisper import WhisperModel
            except Exception as error:
                self.lastError = f"Faster-Whisper is unavailable: {error}"
                self.initialized = False
                if self.logger:
                    self.logger.error(self.lastError)
                return None

            try:
                self.model = WhisperModel(self.modelName, device=self.device, compute_type=self.computeType)
                self.initialized = True
                elapsed = time.perf_counter() - start
                if self.logger:
                    self.logger.info(
                        f"Loaded Whisper model '{self.modelName}' on {self.device} "
                        f"({self.computeType}) in {elapsed:.3f}s"
                    )
                return self.model
            except Exception as error:
                self.model = None
                self.initialized = False
                self.lastError = str(error)
                if self.logger:
                    self.logger.error(f"Failed to load Whisper model: {error}")
                return None

    def transcribe(self, audioPath: str) -> str:
        """Return plain text transcription for a local audio file."""

        result = self.transcribeDetailed(audioPath)
        return result.text if result.success else ""

    def transcribeDetailed(self, audioPath: str) -> TranscriptionResult:
        """Return a structured transcription result for a local audio file."""

        audioDuration = self._measureAudioDuration(audioPath)
        model = self.initialize()
        if model is None:
            result = TranscriptionResult(
                success=False,
                language="",
                transcriptionTime=0.0,
                audioDuration=audioDuration,
                errorMessage=self.lastError or "Speech-to-text model is unavailable.",
            )
            self.lastResult = result
            return result

        try:
            start = time.perf_counter()
            segments, info = model.transcribe(
                str(audioPath),
                language="en",
                beam_size=1,
                vad_filter=False,
            )
            text = " ".join(segment.text for segment in segments).strip()
            duration = time.perf_counter() - start
            language = str(getattr(info, "language", "") or "en")
            if self.logger:
                self.logger.info(
                    f"Transcribed {Path(audioPath).name} in {duration:.3f}s "
                    f"({audioDuration:.3f}s audio, language={language})"
                )
                self.logger.debug(f"Transcription text: {text}")

            result = TranscriptionResult(
                text=text,
                success=bool(text),
                language=language,
                transcriptionTime=duration,
                audioDuration=audioDuration,
                errorMessage="" if text else "Empty transcription.",
            )
            self.lastResult = result
            return result
        except Exception as error:
            duration = time.perf_counter() - start
            message = str(error)
            self.lastError = message
            if self.logger:
                self.logger.error(f"Transcription failed for {audioPath}: {error}")
            result = TranscriptionResult(
                text="",
                success=False,
                language="",
                transcriptionTime=duration,
                audioDuration=audioDuration,
                errorMessage=message,
            )
            self.lastResult = result
            return result

    def shutdown(self):
        """Release the cached model reference."""

        if self.logger:
            self.logger.info("Shutting down speech-to-text model cache.")
        self.model = None
        self.initialized = False

    @staticmethod
    def _measureAudioDuration(audioPath: str) -> float:
        """Return the WAV duration in seconds when possible."""

        try:
            with wave.open(str(audioPath), "rb") as handle:
                frames = handle.getnframes()
                sampleRate = handle.getframerate() or 1
                return frames / float(sampleRate)
        except Exception:
            return 0.0
