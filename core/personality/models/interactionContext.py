"""Short-term interaction context for personality decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass
class InteractionContext:
    """State used to decide tone, humor, and suggestions."""

    currentTask: str = ""
    conversationIntensity: float = 0.0
    interfaceType: str = "text"
    recentAssistantActivity: list[dict] = field(default_factory=list)
    suggestionTimestamps: list[float] = field(default_factory=list)
    lastUserInput: str = ""
    lastResponse: str = ""
    lastUpdated: float = field(default_factory=time)

    def recordActivity(self, activityType: str, details: dict | None = None):
        """Record a bounded activity event."""

        self.recentAssistantActivity.append(
            {"type": str(activityType), "details": details or {}, "timestamp": time()}
        )
        self.recentAssistantActivity = self.recentAssistantActivity[-20:]
        self.lastUpdated = time()

    def recordSuggestion(self):
        """Record a suggestion emission timestamp."""

        self.suggestionTimestamps.append(time())
        self.suggestionTimestamps = self.suggestionTimestamps[-20:]
        self.lastUpdated = time()

    def suggestionsInLastHour(self) -> int:
        """Return how many suggestions were emitted in the last hour."""

        cutoff = time() - 3600
        self.suggestionTimestamps = [item for item in self.suggestionTimestamps if item >= cutoff]
        return len(self.suggestionTimestamps)

    def asDict(self) -> dict:
        """Return a serializable context snapshot."""

        return {
            "currentTask": self.currentTask,
            "conversationIntensity": self.conversationIntensity,
            "interfaceType": self.interfaceType,
            "recentAssistantActivity": list(self.recentAssistantActivity),
            "suggestionsInLastHour": self.suggestionsInLastHour(),
            "lastUserInput": self.lastUserInput,
            "lastResponse": self.lastResponse,
            "lastUpdated": self.lastUpdated,
        }

