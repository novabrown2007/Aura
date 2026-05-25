"""Conversation summary model for persisted assistant continuity."""

from __future__ import annotations

from dataclasses import dataclass, field

from auraassistant.core.memory.models.memory import utcNow


@dataclass
class MemorySummary:
    """Compact summary of a completed conversation or session."""

    summary: str
    facts: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    sessionId: str = ""
    createdAt: str = field(default_factory=utcNow)

    def asDict(self) -> dict:
        """Return a serializable summary."""

        return {
            "summary": self.summary,
            "facts": list(self.facts),
            "tags": list(self.tags),
            "sessionId": self.sessionId,
            "createdAt": self.createdAt,
        }

