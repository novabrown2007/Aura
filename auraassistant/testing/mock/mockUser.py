"""Mock assistant user flows for testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MockUser:
    """Simulate typed and voice-based user interactions."""

    name: str = "Nova"
    history: list[dict[str, Any]] = field(default_factory=list)

    def typedInput(self, text: str):
        """Record a typed input event."""

        payload = {"type": "typed", "text": str(text or "")}
        self.history.append(payload)
        return payload

    def voiceInput(self, text: str):
        """Record a simulated voice input event."""

        payload = {"type": "voice", "text": str(text or "")}
        self.history.append(payload)
        return payload

    def repeatRequest(self, text: str, count: int = 2):
        """Generate a repeated request flow."""

        results = [self.typedInput(text) for _ in range(max(1, int(count)))]
        return results

    def clarificationFlow(self, question: str, answer: str):
        """Simulate a clarification exchange."""

        return {
            "question": self.typedInput(question),
            "answer": self.typedInput(answer),
        }
