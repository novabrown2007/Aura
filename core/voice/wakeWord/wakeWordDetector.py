"""OpenWakeWord detector wrapper for Aura."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.request import urlretrieve

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
        self.modelReadinessWarning = ""
        self.fallbackActive = False
        self.fallbackReason = ""
        self.predictionCount = 0
        self.totalPredictionTimeMs = 0.0

    def initialize(self):
        """Initialize OpenWakeWord exactly once."""

        if self.initialized and self.model is not None:
            return self.model
        try:
            missingCustomModels = self._missingCustomModelPhrases()
            modelNames = self._wakeWordModels()
            if missingCustomModels:
                detail = (
                    "OpenWakeWord needs local custom model files for configured wake phrases: "
                    f"{', '.join(missingCustomModels)}. Add .onnx/.tflite models to "
                    "core/voice/wakeWord/models or set voice.alwaysActive.wakeWordModelPath."
                )
                if modelNames:
                    self.modelReadinessWarning = f"{detail} Continuing with available configured wake model(s)."
                    if self.logger:
                        self.logger.warning(self.modelReadinessWarning)
                elif self.config.wakeWordAllowPretrainedFallback:
                    fallbackModel = self._pretrainedFallbackModel()
                    modelNames = [fallbackModel]
                    self.activeWakePhrases = [fallbackModel]
                    self.fallbackActive = True
                    self.fallbackReason = detail
                    self.modelReadinessWarning = (
                        f"{detail} Falling back to built-in OpenWakeWord model '{fallbackModel}' so "
                        "always-active listening can start."
                    )
                    if self.logger:
                        self.logger.warning(self.modelReadinessWarning)
                else:
                    self.modelReadinessWarning = detail
                    if self.logger:
                        self.logger.warning(self.modelReadinessWarning)
                    raise RuntimeError(self.modelReadinessWarning)

            import openwakeword
            self._ensureOpenWakeWordAssets(openwakeword, modelNames)
            from openwakeword.model import Model

            kwargs = {"inference_framework": self.config.wakeWordInferenceFramework}
            if modelNames:
                kwargs["wakeword_models"] = modelNames
            self.model = Model(**kwargs)
            self.initialized = True
            self.lastError = ""
            if self.logger:
                phrase = self.activeWakePhrases[0] if self.fallbackActive and self.activeWakePhrases else self.config.wakeWordPhrase
                self.logger.info(f"OpenWakeWord model initialized for phrase '{phrase}'.")
            return self.model
        except Exception as error:
            detail = str(error)
            if self.modelReadinessWarning and self.modelReadinessWarning not in detail:
                detail = f"{detail}. {self.modelReadinessWarning}"
            self.lastError = detail
            self.initialized = False
            if self.logger:
                self.logger.error(f"OpenWakeWord model initialization failed: {detail}")
            raise RuntimeError(detail) from error

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
            if self.config.wakeWordDebugLogging:
                self._writeDebugPrediction(result)
            return result
        except Exception as error:
            self.lastError = str(error)
            result = WakeWordResult(phrase=self.config.wakeWordPhrase, errorMessage=str(error))
            self.lastResult = result
            if self.logger:
                self.logger.error(f"Wake word prediction failed: {error}")
            return result

    def reset(self):
        """Reset detector buffers so completed activations do not retrigger."""

        try:
            if self.model is not None and hasattr(self.model, "reset"):
                self.model.reset()
            self.lastResult = WakeWordResult(phrase=self.config.wakeWordPhrase)
            self.lastError = ""
        except Exception as error:
            self.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Wake word detector reset failed: {error}")

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
            "modelReadinessWarning": self.modelReadinessWarning,
            "fallbackActive": self.fallbackActive,
            "fallbackModel": self.config.wakeWordFallbackModel,
            "fallbackReason": self.fallbackReason,
            "missingCustomModelPhrases": self._missingCustomModelPhrases(),
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

            normalizedPhrase = _normalizePhrase(phrase)
            if normalizedPhrase in _OPENWAKEWORD_PRETRAINED_MODELS:
                models.append(normalizedPhrase)
                continue

            modelDirectory = Path(__file__).resolve().parent / "models"
            localModel = None
            modelNames = [phrase, normalizedPhrase]
            for suffix in (".onnx", ".tflite"):
                for modelName in modelNames:
                    localPath = modelDirectory / f"{modelName}{suffix}"
                    if localPath.exists():
                        localModel = str(localPath)
                        break
                if localModel:
                    break
            if localModel:
                models.append(localModel)

        return models

    def _missingCustomModelPhrases(self) -> list[str]:
        missing = []
        for phrase in self.config.validWakeWordPhrases():
            normalized = _normalizePhrase(phrase)
            if normalized in _OPENWAKEWORD_PRETRAINED_MODELS:
                continue
            if self._localModelPathForPhrase(phrase) is None:
                missing.append(str(phrase))
        return missing

    def _pretrainedFallbackModel(self) -> str:
        """Return a valid built-in fallback model name."""

        fallbackModel = _normalizePhrase(self.config.wakeWordFallbackModel or "hey_jarvis")
        if fallbackModel in _OPENWAKEWORD_PRETRAINED_MODELS:
            return fallbackModel
        if self.logger:
            self.logger.warning(
                f"Invalid wakeWordFallbackModel '{self.config.wakeWordFallbackModel}'. "
                "Using built-in fallback 'hey_jarvis'."
            )
        return "hey_jarvis"

    def _ensureOpenWakeWordAssets(self, openwakewordModule: Any, modelNames: list[str]):
        """Download missing OpenWakeWord assets needed by the selected models."""

        if not self.config.wakeWordAutoDownloadModels:
            return

        requiredAssets = []
        framework = str(self.config.wakeWordInferenceFramework or "onnx").strip().lower()

        for modelName in modelNames:
            if Path(str(modelName)).expanduser().exists():
                continue
            modelAsset = self._assetForPretrainedModel(openwakewordModule, str(modelName), framework)
            if modelAsset is not None:
                requiredAssets.append(modelAsset)

        for assetName in ("melspectrogram", "embedding"):
            featureAsset = self._assetForFeatureModel(openwakewordModule, assetName, framework)
            if featureAsset is not None:
                requiredAssets.append(featureAsset)

        for path, url in self._deduplicateAssets(requiredAssets):
            if path.exists():
                continue
            self._downloadAsset(path, url)

    def _assetForPretrainedModel(self, openwakewordModule: Any, modelName: str, framework: str) -> tuple[Path, str] | None:
        """Return the expected path and download URL for a pretrained model."""

        models = getattr(openwakewordModule, "MODELS", {}) or {}
        normalized = _normalizePhrase(modelName)
        metadata = models.get(normalized)
        if not metadata:
            return None
        return self._assetFromMetadata(metadata, framework)

    def _assetForFeatureModel(self, openwakewordModule: Any, assetName: str, framework: str) -> tuple[Path, str] | None:
        """Return the expected path and download URL for a feature model."""

        features = getattr(openwakewordModule, "FEATURE_MODELS", {}) or {}
        metadata = features.get(assetName)
        if not metadata:
            return None
        return self._assetFromMetadata(metadata, framework)

    @staticmethod
    def _assetFromMetadata(metadata: dict, framework: str) -> tuple[Path, str] | None:
        """Convert OpenWakeWord metadata to the configured framework asset."""

        modelPath = str(metadata.get("model_path") or "")
        downloadUrl = str(metadata.get("download_url") or "")
        if not modelPath or not downloadUrl:
            return None
        if framework == "onnx":
            modelPath = modelPath.replace(".tflite", ".onnx")
            downloadUrl = downloadUrl.replace(".tflite", ".onnx")
        elif framework == "tflite":
            modelPath = modelPath.replace(".onnx", ".tflite")
            downloadUrl = downloadUrl.replace(".onnx", ".tflite")
        return Path(modelPath), downloadUrl

    @staticmethod
    def _deduplicateAssets(assets: list[tuple[Path, str]]) -> list[tuple[Path, str]]:
        """Deduplicate assets while preserving order."""

        seen = set()
        deduplicated = []
        for path, url in assets:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append((path, url))
        return deduplicated

    def _downloadAsset(self, path: Path, url: str):
        """Download one missing OpenWakeWord model asset."""

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if self.logger:
                self.logger.info(f"Downloading OpenWakeWord asset: {path.name}")
            urlretrieve(url, path)
        except Exception as error:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
            raise RuntimeError(f"OpenWakeWord asset download failed for {path.name}: {error}") from error

    @staticmethod
    def _localModelPathForPhrase(phrase: str) -> Path | None:
        phrasePath = Path(str(phrase or "").strip()).expanduser()
        if phrasePath.exists():
            return phrasePath
        modelDirectory = Path(__file__).resolve().parent / "models"
        modelNames = [str(phrase or "").strip(), _normalizePhrase(phrase)]
        for suffix in (".onnx", ".tflite"):
            for modelName in modelNames:
                localPath = modelDirectory / f"{modelName}{suffix}"
                if localPath.exists():
                    return localPath
        return None

    def _writeDebugPrediction(self, result: WakeWordResult):
        """Append wake-word prediction diagnostics when debug logging is enabled."""

        try:
            debugDirectory = Path(self.config.wakeWordDebugLoggingLocation or "logs/wake_word")
            debugDirectory.mkdir(parents=True, exist_ok=True)
            path = debugDirectory / "wake_word_predictions.log"
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(
                    f"{datetime.now().isoformat(timespec='milliseconds')} "
                    f"phrase={result.phrase!r} model={result.modelName!r} "
                    f"confidence={result.confidence:.4f} detected={result.detected} "
                    f"predictionTimeMs={result.predictionTimeMs:.3f}\n"
                )
        except Exception as error:
            self.lastError = str(error)
            if self.logger:
                self.logger.warning(f"Wake word debug prediction log failed: {error}")

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


_OPENWAKEWORD_PRETRAINED_MODELS = {
    "alexa",
    "hey_mycroft",
    "hey_jarvis",
    "hey_rhasspy",
    "current_weather",
    "timers",
}
