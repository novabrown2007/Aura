"""Mock voice input payloads for assistant simulation tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class MockVoiceInput:
    """Represent a simulated push-to-talk audio request."""

    text: str
    sampleRate: int = 16000
    durationSeconds: float = 1.0
    language: str = "en"

    def toDict(self) -> dict[str, Any]:
        """Return a deterministic simulated voice request."""

        return {
            "audioId": uuid4().hex,
            "text": self.text,
            "sampleRate": self.sampleRate,
            "durationSeconds": self.durationSeconds,
            "language": self.language,
        }

    @classmethod
    def create(cls, text: str, **kwargs):
        """Create a simulated voice input case."""

        return cls(text=str(text or ""), **kwargs)

    @classmethod
    def fromText(cls, text: str, **kwargs):
        """Alias for create for readability in tests."""

        return cls.create(text, **kwargs)

    def toTranscriptionCase(self) -> dict[str, Any]:
        """Return a mock transcription payload for tests."""

        return {
            "text": self.text,
            "language": self.language,
            "sampleRate": self.sampleRate,
            "durationSeconds": self.durationSeconds,
        }
