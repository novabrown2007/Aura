"""Configurable assistant personality profile."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonalityProfile:
    """Runtime personality settings for Aura."""

    personalityEnabled: bool = True
    humorEnabled: bool = True
    suggestionsEnabled: bool = True
    initiativeLevel: float = 0.35
    verbosity: str = "normal"
    tone: str = "casual"
    personalityStrength: float = 0.35
    maxSuggestionsPerHour: int = 3

    @classmethod
    def fromContext(cls, context=None):
        """Build a profile from Aura configuration."""

        config = getattr(context, "config", None)

        def get(key: str, default):
            if config is None or not hasattr(config, "get"):
                return default
            value = config.get(key, None)
            return default if value is None else value

        def getBool(key: str, default: bool) -> bool:
            value = get(key, default)
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in {"1", "true", "yes", "on"}

        return cls(
            personalityEnabled=getBool("personality.personalityEnabled", True),
            humorEnabled=getBool("personality.humorEnabled", True),
            suggestionsEnabled=getBool("personality.suggestionsEnabled", True),
            initiativeLevel=float(get("personality.initiativeLevel", 0.35)),
            verbosity=str(get("personality.verbosity", "normal") or "normal"),
            tone=str(get("personality.toneMode", get("personality.tone", "casual")) or "casual"),
            personalityStrength=float(get("personality.personalityStrength", 0.35)),
            maxSuggestionsPerHour=int(get("personality.maxSuggestionsPerHour", 3)),
        )

    def asDict(self) -> dict:
        """Return a serializable profile."""

        return {
            "personalityEnabled": self.personalityEnabled,
            "humorEnabled": self.humorEnabled,
            "suggestionsEnabled": self.suggestionsEnabled,
            "initiativeLevel": self.initiativeLevel,
            "verbosity": self.verbosity,
            "tone": self.tone,
            "personalityStrength": self.personalityStrength,
            "maxSuggestionsPerHour": self.maxSuggestionsPerHour,
        }

