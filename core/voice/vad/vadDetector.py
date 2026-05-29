"""Silero-backed realtime voice activity detector."""

from __future__ import annotations

from time import time
from typing import Any

from core.voice.vad.configuration import VADConfig
from core.voice.vad.models import VADResult


class VADDetector:
    """Analyze audio frames and return speech probability results."""

    def __init__(self, context=None, config: VADConfig | None = None):
        self.context = context
        self.config = config or VADConfig.fromContext(context)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Voice.VAD.Detector") if logger else None
        self.model = None
        self.backend = ""
        self.initialized = False
        self.lastResult = VADResult(threshold=self.config.vadSpeechThreshold)
        self.lastError = ""
        self._torch = None
        self._numpy = None

    def initialize(self) -> bool:
        """Load Silero VAD when available, with safe energy fallback."""

        if self.initialized:
            return True
        try:
            import numpy as numpyModule

            self._numpy = numpyModule
        except Exception as error:
            self.lastError = f"numpy is unavailable: {error}"
            self.backend = "unavailable"
            return False

        try:
            import torch

            torch.set_num_threads(1)
            model, _utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                trust_repo=True,
            )
            self._torch = torch
            self.model = model
            self.backend = "silero"
            self.initialized = True
            if self.logger:
                self.logger.info("Silero VAD model loaded through PyTorch Hub.")
            return True
        except Exception as error:
            self.lastError = str(error)
            self.backend = "energy"
            self.initialized = True
            if self.logger:
                self.logger.warning(f"Silero VAD unavailable; using energy fallback: {error}")
            return True

    def detect(self, audioFrame: Any, sampleRate: int | None = None) -> VADResult:
        """Return speech confidence for one microphone frame."""

        if not self.initialized:
            self.initialize()

        timestamp = time()
        try:
            samples = self._toFloatMono(audioFrame)
            sampleRate = int(sampleRate or self.config.vadSampleRate)
            if samples is None or samples.size == 0:
                result = VADResult(False, 0.0, self.config.vadSpeechThreshold, timestamp, self.backend)
            elif self.backend == "silero" and self.model is not None and self._torch is not None:
                tensor = self._torch.from_numpy(samples)
                confidence = float(self.model(tensor, sampleRate).item())
                result = VADResult(
                    isSpeech=confidence >= float(self.config.vadSpeechThreshold),
                    confidence=confidence,
                    threshold=float(self.config.vadSpeechThreshold),
                    timestamp=timestamp,
                    backend="silero",
                )
            else:
                confidence = self._energyConfidence(samples)
                result = VADResult(
                    isSpeech=confidence >= float(self.config.vadSpeechThreshold),
                    confidence=confidence,
                    threshold=float(self.config.vadSpeechThreshold),
                    timestamp=timestamp,
                    backend=self.backend or "energy",
                )
            self.lastResult = result
            return result
        except Exception as error:
            self.lastError = str(error)
            result = VADResult(
                isSpeech=False,
                confidence=0.0,
                threshold=float(self.config.vadSpeechThreshold),
                timestamp=timestamp,
                backend=self.backend,
                errorMessage=str(error),
            )
            self.lastResult = result
            if self.logger:
                self.logger.error(f"VAD detection failed: {error}")
            return result

    def reset(self):
        """Reset detector state when supported by the backend."""

        try:
            if self.model is not None and hasattr(self.model, "reset_states"):
                self.model.reset_states()
        except Exception as error:
            if self.logger:
                self.logger.debug(f"VAD detector reset failed: {error}")

    def snapshot(self) -> dict:
        """Return detector diagnostics."""

        return {
            "initialized": self.initialized,
            "backend": self.backend,
            "lastResult": self.lastResult.asDict(),
            "lastError": self.lastError,
        }

    def _toFloatMono(self, audioFrame: Any):
        np = self._numpy
        if np is None:
            return None
        audio = np.asarray(audioFrame)
        if audio.ndim > 1:
            audio = audio[:, 0]
        if audio.dtype.kind in {"i", "u"}:
            audio = audio.astype(np.float32) / 32768.0
        else:
            audio = audio.astype(np.float32)
        return audio.reshape(-1)

    def _energyConfidence(self, samples) -> float:
        """Map RMS energy to a rough 0..1 speech confidence fallback."""

        np = self._numpy
        if np is None:
            return 0.0
        rms = float(np.sqrt(np.mean(np.square(samples)))) if samples.size else 0.0
        return max(0.0, min(1.0, rms / 0.08))

