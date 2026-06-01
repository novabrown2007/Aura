"""Context payload attached to structured assistant responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResponseContext:
    """Attach runtime state to one assistant response."""

    conversation: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    interface: dict[str, Any] = field(default_factory=dict)
    interruption: dict[str, Any] = field(default_factory=dict)
    clarification: dict[str, Any] = field(default_factory=dict)
    sessionId: str = ""
    userInput: str = ""

    def asDict(self) -> dict[str, Any]:
        return {
            "conversation": dict(self.conversation or {}),
            "memory": dict(self.memory or {}),
            "interface": dict(self.interface or {}),
            "interruption": dict(self.interruption or {}),
            "clarification": dict(self.clarification or {}),
            "sessionId": self.sessionId,
            "userInput": self.userInput,
        }
