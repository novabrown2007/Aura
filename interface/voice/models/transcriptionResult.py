"""Structured transcription result for local voice input."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TranscriptionResult:
    """Normalized transcription output from the local speech-to-text stack."""

    text: str = ""
    success: bool = False
    language: str = ""
    transcriptionTime: float = 0.0
    audioDuration: float = 0.0
    errorMessage: str = ""

    def toDict(self) -> dict[str, object]:
        """Return a clean dictionary representation."""

        return {
            "text": self.text,
            "success": self.success,
            "language": self.language,
            "transcriptionTime": self.transcriptionTime,
            "audioDuration": self.audioDuration,
            "errorMessage": self.errorMessage,
        }

    def __bool__(self) -> bool:
        return bool(self.success and self.text.strip())

