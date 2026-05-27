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
    wakeWordFrameDurationMs: int = 80
    wakeWordSampleRate: int = 16000
    wakeWordCaptureSeconds: float = 5.0

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

        def nested_or_flat(name: str, default: Any = None):
            return value(name, value(f"voice.wakeWord.{name}", value(f"wakeWord.{name}", default)))

        activePhrase = str(nested_or_flat("wakeWordPhrase", "hey_aura")).strip() or "hey_aura"
        configuredPhrases = _string_list(nested_or_flat("wakeWordPhrases", [activePhrase]))
        if activePhrase not in configuredPhrases:
            configuredPhrases.insert(0, activePhrase)

        return cls(
            wakeWordEnabled=_bool(nested_or_flat("wakeWordEnabled", True), True),
            wakeWordPhrase=activePhrase,
            wakeWordPhrases=configuredPhrases,
            wakeWordSensitivity=_float(nested_or_flat("wakeWordSensitivity", 0.5), 0.5),
            wakeWordCooldownSeconds=_float(nested_or_flat("wakeWordCooldownSeconds", 5.0), 5.0),
            wakeWordMicrophoneDevice=nested_or_flat("wakeWordMicrophoneDevice", None),
            wakeWordModelPath=str(nested_or_flat("wakeWordModelPath", "")),
            wakeWordInferenceFramework=str(nested_or_flat("wakeWordInferenceFramework", "onnx")),
            wakeWordAutoStart=_bool(nested_or_flat("wakeWordAutoStart", True), True),
            wakeWordDebugLogging=_bool(nested_or_flat("wakeWordDebugLogging", False), False),
            wakeWordFrameDurationMs=int(_float(nested_or_flat("wakeWordFrameDurationMs", 80), 80)),
            wakeWordSampleRate=int(_float(nested_or_flat("wakeWordSampleRate", 16000), 16000)),
            wakeWordCaptureSeconds=_float(nested_or_flat("wakeWordCaptureSeconds", 5.0), 5.0),
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
