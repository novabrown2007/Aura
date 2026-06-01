"""Spoken response payload for Aura."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SpokenResponse:
    """Optimized speech payload for TTS delivery."""

    text: str = ""
    tone: str = "neutral"
    concise: bool = True

    def asDict(self) -> dict[str, object]:
        return {"text": self.text, "tone": self.tone, "concise": bool(self.concise)}
