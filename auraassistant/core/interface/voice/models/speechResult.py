"""Structured speech synthesis result for Aura."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SpeechResult:
    """Normalized text-to-speech output from Aura's local voice stack."""

    success: bool = False
    audioPath: str = ""
    generationTime: float = 0.0
    playbackDuration: float = 0.0
    errorMessage: str = ""

    def toDict(self) -> dict[str, object]:
        """Return a clean dictionary representation."""

        return {
            "success": self.success,
            "audioPath": self.audioPath,
            "generationTime": self.generationTime,
            "playbackDuration": self.playbackDuration,
            "errorMessage": self.errorMessage,
        }

    def __bool__(self) -> bool:
        return bool(self.success)
