"""Configuration model for Aura's local wake word subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WakeWordConfig:
    """Typed wake word configuration with conservative runtime defaults."""

    wakeWordEnabled: bool = True
    wakeWordPhrase: str = "hey_aura"
    wakeWordPhrases: list[str] | None = None
    wakeWordSensitivity: float = 0.5
    wakeWordCooldownSeconds: float = 5.0
    wakeWordMicrophoneDevice: str | int | None = None
    wakeWordModelPath: str = ""
    wakeWordInferenceFramework: str = "onnx"
    wakeWordAutoStart: bool = True
    wakeWordDebugLogging: bool = False
    wakeWordDebugLoggingLocation: str = "logs/wake_word"
    wakeWordFrameDurationMs: int = 80
    wakeWordSampleRate: int = 16000
    wakeWordCaptureSeconds: float = 5.0
    wakeWordResumeDelaySeconds: float = 1.5
    wakeWordAllowPretrainedFallback: bool = True
    wakeWordFallbackModel: str = "hey_jarvis"
    wakeWordAutoDownloadModels: bool = True

    @classmethod
    def fromContext(cls, context=None) -> "WakeWordConfig":
        """Build config from Aura's config loader using flat and nested keys."""

        config = getattr(context, "config", None)

        def value(key: str, default: Any = None):
            if config is None or not hasattr(config, "get"):
                return default
            result = config.get(key, default)
            if result in (None, ""):
                return default
            return result

        def first_value(keys: list[str], default: Any = None):
            for key in keys:
                result = value(key, None)
                if result not in (None, ""):
                    return result
            return default

        def nested_or_flat(name: str, default: Any = None):
            return first_value(
                [
                    f"voice.alwaysActive.{name}",
                    f"voice.wakeWord.{name}",
                    f"wakeWord.{name}",
                    name,
                ],
                default,
            )

        configuredPhrases = _string_list(
            first_value(
                [
                    "voice.alwaysActive.activationPhrases",
                    "voice.alwaysActive.wakeWordPhrases",
                    "voice.wakeWord.activationPhrases",
                    "voice.wakeWord.wakeWordPhrases",
                    "activationPhrases",
                    "wakeWordPhrases",
                ],
                [],
            )
        )
        activePhrase = str(
            first_value(
                [
                    "voice.alwaysActive.activationPhrase",
                    "voice.alwaysActive.wakeWordPhrase",
                    "voice.wakeWord.activationPhrase",
                    "voice.wakeWord.wakeWordPhrase",
                    "activationPhrase",
                    "wakeWordPhrase",
                ],
                "",
            )
        ).strip()
        if not activePhrase and configuredPhrases:
            activePhrase = configuredPhrases[0]
        if not activePhrase:
            activePhrase = "Hey Aura"
        if not configuredPhrases:
            configuredPhrases = [activePhrase]
        if activePhrase not in configuredPhrases:
            configuredPhrases.insert(0, activePhrase)

        return cls(
            wakeWordEnabled=_bool(
                first_value(
                    [
                        "voice.alwaysActive.enabled",
                        "voice.alwaysActive.wakeWordEnabled",
                        "voice.wakeWord.enabled",
                        "voice.wakeWord.wakeWordEnabled",
                        "alwaysActive.enabled",
                        "wakeWordEnabled",
                        "enabled",
                    ],
                    True,
                ),
                True,
            ),
            wakeWordPhrase=activePhrase,
            wakeWordPhrases=configuredPhrases,
            wakeWordSensitivity=_float(nested_or_flat("wakeWordSensitivity", 0.5), 0.5),
            wakeWordCooldownSeconds=_float(nested_or_flat("wakeWordCooldownSeconds", 5.0), 5.0),
            wakeWordMicrophoneDevice=nested_or_flat("wakeWordMicrophoneDevice", None),
            wakeWordModelPath=str(nested_or_flat("wakeWordModelPath", "")),
            wakeWordInferenceFramework=str(nested_or_flat("wakeWordInferenceFramework", "onnx")),
            wakeWordAutoStart=_bool(nested_or_flat("wakeWordAutoStart", True), True),
            wakeWordDebugLogging=_bool(nested_or_flat("wakeWordDebugLogging", False), False),
            wakeWordDebugLoggingLocation=str(nested_or_flat("wakeWordDebugLoggingLocation", "logs/wake_word")),
            wakeWordFrameDurationMs=int(_float(nested_or_flat("wakeWordFrameDurationMs", 80), 80)),
            wakeWordSampleRate=int(_float(nested_or_flat("wakeWordSampleRate", 16000), 16000)),
            wakeWordCaptureSeconds=_float(nested_or_flat("wakeWordCaptureSeconds", 5.0), 5.0),
            wakeWordResumeDelaySeconds=_float(nested_or_flat("wakeWordResumeDelaySeconds", 1.5), 1.5),
            wakeWordAllowPretrainedFallback=_bool(nested_or_flat("wakeWordAllowPretrainedFallback", True), True),
            wakeWordFallbackModel=str(nested_or_flat("wakeWordFallbackModel", "hey_jarvis")),
            wakeWordAutoDownloadModels=_bool(nested_or_flat("wakeWordAutoDownloadModels", True), True),
        )

    def validWakeWordPhrases(self) -> list[str]:
        """Return normalized configured wake words/phrases."""

        phrases = _string_list(self.wakeWordPhrases or [])
        active = str(self.wakeWordPhrase or "").strip()
        if active and active not in phrases:
            phrases.insert(0, active)
        return phrases or ["hey_aura"]

    def isValidWakeWord(self, phrase: str) -> bool:
        """Return whether a predicted wake phrase is allowed by configuration."""

        candidate = _normalize_phrase(phrase)
        return candidate in {_normalize_phrase(item) for item in self.validWakeWordPhrases()}


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        rawItems = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        rawItems = list(value)
    else:
        rawItems = [value]

    items = []
    seen = set()
    for item in rawItems:
        text = str(item or "").strip()
        if not text:
            continue
        if text not in seen:
            seen.add(text)
            items.append(text)
    return items


def _normalize_phrase(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_")
