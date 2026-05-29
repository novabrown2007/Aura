"""Configuration for Aura's voice activity detection system."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VADConfig:
    """Runtime tunables for endpoint detection."""

    vadEnabled: bool = True
    vadSilenceThresholdSeconds: float = 1.2
    vadSpeechThreshold: float = 0.5
    vadMinSpeechDuration: float = 0.3
    vadMaxRecordingDuration: float = 30.0
    vadDebugLogging: bool = True
    vadSampleRate: int = 16000

    @classmethod
    def fromContext(cls, context=None):
        """Build VAD config from Aura's config loader."""

        config = getattr(context, "config", None)

        def get(key: str, default):
            if config is None or not hasattr(config, "get"):
                return default
            value = config.get(key, None)
            if value is None:
                return default
            return value

        def getBool(key: str, default: bool) -> bool:
            value = get(key, default)
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            vadEnabled=getBool("voice.vad.vadEnabled", getBool("voice.vad.enabled", getBool("vadEnabled", True))),
            vadSilenceThresholdSeconds=float(
                get("voice.vad.vadSilenceThresholdSeconds", get("vadSilenceThresholdSeconds", 1.2))
            ),
            vadSpeechThreshold=float(get("voice.vad.vadSpeechThreshold", get("vadSpeechThreshold", 0.5))),
            vadMinSpeechDuration=float(get("voice.vad.vadMinSpeechDuration", get("vadMinSpeechDuration", 0.3))),
            vadMaxRecordingDuration=float(get("voice.vad.vadMaxRecordingDuration", get("vadMaxRecordingDuration", 30))),
            vadDebugLogging=getBool("voice.vad.vadDebugLogging", getBool("vadDebugLogging", True)),
            vadSampleRate=int(get("voice.STT.sampleRate", get("voice.sampleRate", 16000))),
        )
