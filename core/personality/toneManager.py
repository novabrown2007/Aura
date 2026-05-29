"""Tone management for Aura responses."""

from __future__ import annotations


class ToneManager:
    """Map interface and configuration into stable tone guidance."""

    supportedModes = {"casual", "professional", "concise", "developer", "voice"}

    def __init__(self, profile, logger=None):
        self.profile = profile
        self.logger = logger

    def setTone(self, tone: str):
        """Set tone if supported."""

        normalized = self.normalizeTone(tone)
        self.profile.tone = normalized
        if self.logger:
            self.logger.info(f"Personality tone set to {normalized}.")
        return normalized

    def toneForContext(self, interactionContext) -> str:
        """Return the effective tone for the current interface."""

        if str(getattr(interactionContext, "interfaceType", "")).lower() == "voice":
            return "voice"
        return self.normalizeTone(self.profile.tone)

    def promptInstructions(self, interactionContext=None) -> str:
        """Return provider-facing tone instructions."""

        tone = self.toneForContext(interactionContext) if interactionContext else self.normalizeTone(self.profile.tone)
        instructions = {
            "casual": "Use a natural, warm, low-drama conversational tone.",
            "professional": "Use a polished, direct, professional tone.",
            "concise": "Be brief and avoid extra commentary.",
            "developer": "Use precise engineering language and keep implementation details clear.",
            "voice": "Use short, speakable sentences suitable for TTS.",
        }
        return instructions.get(tone, instructions["casual"])

    @classmethod
    def normalizeTone(cls, tone: str) -> str:
        normalized = str(tone or "casual").strip().lower()
        if normalized == "brief":
            normalized = "concise"
        return normalized if normalized in cls.supportedModes else "casual"

