"""OpenWakeWord detector wrapper for Aura."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from .configuration import WakeWordConfig
from .models import WakeWordResult


class WakeWordDetector:
    """Load OpenWakeWord once and evaluate microphone PCM frames."""

    def __init__(self, context=None, config: WakeWordConfig | None = None):
        self.context = context
        self.config = config or WakeWordConfig.fromContext(context)
        self.logger = context.logger.getChild("Voice.WakeWord.Detector") if context and getattr(context, "logger", None) else None
        self.model = None
        self.initialized = False
        self.lastResult = WakeWordResult(phrase=self.config.wakeWordPhrase)
        self.activeWakePhrases = self.config.validWakeWordPhrases()
        self.lastError = ""
        self.predictionCount = 0
        self.totalPredictionTimeMs = 0.0

    def initialize(self):
        """Initialize OpenWakeWord exactly once."""

        if self.initialized and self.model is not None:
            return self.model
        try:
            from openwakeword.model import Model

            modelNames = self._wakeWordModels()
            kwargs = {"inference_framework": self.config.wakeWordInferenceFramework}
            if modelNames:
                kwargs["wakeword_models"] = modelNames
            self.model = Model(**kwargs)
            self.initialized = True
            self.lastError = ""
            if self.logger:
                self.logger.info(f"OpenWakeWord model initialized for phrase '{self.config.wakeWordPhrase}'.")
            return self.model
        except Exception as error:
            self.lastError = str(error)
            self.initialized = False
            if self.logger:
                self.logger.error(f"OpenWakeWord model initialization failed: {error}")
            raise

    def processFrame(self, frame: Any) -> WakeWordResult:
        """Run prediction for one PCM frame and return a normalized result."""

        if frame is None:
            return WakeWordResult(phrase=self.config.wakeWordPhrase, errorMessage="Empty audio frame.")
        try:
            model = self.initialize()
            start = perf_counter()
            predictions = model.predict(frame)
            predictionTimeMs = (perf_counter() - start) * 1000.0
            normalized = self._normalizePredictions(predictions)
            modelName, confidence = self._bestPrediction(normalized, self.activeWakePhrases)
            detected = confidence >= float(self.config.wakeWordSensitivity)
            result = WakeWordResult(
                detected=detected,
                phrase=modelName or self.config.wakeWordPhrase,
                confidence=confidence,
                modelName=modelName,
                predictions=normalized,
                predictionTimeMs=predictionTimeMs,
                frameDurationMs=float(self.config.wakeWordFrameDurationMs),
            )
            self.lastResult = result
            self.predictionCount += 1
            self.totalPredictionTimeMs += predictionTimeMs
            if self.config.wakeWordDebugLogging and self.logger:
                self.logger.debug(f"Wake word prediction confidence={confidence:.3f}, detected={detected}.")
            return result
        except Exception as error:
            self.lastError = str(error)
            result = WakeWordResult(phrase=self.config.wakeWordPhrase, errorMessage=str(error))
            self.lastResult = result
            if self.logger:
                self.logger.error(f"Wake word prediction failed: {error}")
            return result

    def snapshot(self) -> dict:
        """Return detector diagnostics for developer UI and logs."""

        avgMs = self.totalPredictionTimeMs / self.predictionCount if self.predictionCount else 0.0
        return {
            "initialized": self.initialized,
            "phrase": self.config.wakeWordPhrase,
            "validPhrases": list(self.activeWakePhrases),
            "sensitivity": self.config.wakeWordSensitivity,
            "predictionCount": self.predictionCount,
            "averagePredictionTimeMs": avgMs,
            "lastError": self.lastError,
            "lastResult": self.lastResult.asDict(),
        }

    def _wakeWordModels(self) -> list[str]:
        explicitPath = str(self.config.wakeWordModelPath or "").strip()
        if explicitPath:
            return [explicitPath]

        models = []
        for phrase in self.config.validWakeWordPhrases():
            phrase = str(phrase or "").strip()
            if not phrase:
                continue

            phrasePath = Path(phrase).expanduser()
            if phrasePath.exists():
                models.append(str(phrasePath))
                continue

            modelDirectory = Path(__file__).resolve().parent / "models"
            localModel = None
            modelNames = [phrase, _normalizePhrase(phrase)]
            for suffix in (".onnx", ".tflite"):
                for modelName in modelNames:
                    localPath = modelDirectory / f"{modelName}{suffix}"
                    if localPath.exists():
                        localModel = str(localPath)
                        break
                if localModel:
                    break
            models.append(localModel or _normalizePhrase(phrase))

        return models

    @staticmethod
    def _normalizePredictions(predictions: Any) -> dict[str, float]:
        if not isinstance(predictions, dict):
            return {}
        normalized = {}
        for key, value in predictions.items():
            try:
                normalized[str(key)] = float(value)
            except Exception:
                normalized[str(key)] = 0.0
        return normalized

    @staticmethod
    def _bestPrediction(predictions: dict[str, float], validPhrases: list[str] | None = None) -> tuple[str, float]:
        if not predictions:
            return "", 0.0
        allowed = {_normalizePhrase(item) for item in validPhrases or []}
        candidates = {
            key: value
            for key, value in predictions.items()
            if not allowed or _normalizePhrase(key) in allowed
        }
        if not candidates:
            return "", 0.0
        key = max(candidates, key=lambda item: candidates[item])
        return key, float(predictions.get(key, 0.0))


def _normalizePhrase(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_")
