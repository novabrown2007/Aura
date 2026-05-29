"""Developer console snapshot model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConsoleStateSnapshot:
    """Immutable-ish snapshot of current developer UI state."""

    events: list[dict[str, Any]] = field(default_factory=list)
    sessions: list[dict[str, Any]] = field(default_factory=list)
    intents: list[dict[str, Any]] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    voice: dict[str, Any] = field(default_factory=dict)
    providers: dict[str, Any] = field(default_factory=dict)
    bridge: dict[str, Any] = field(default_factory=dict)
    notifications: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    system: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, Any] = field(default_factory=dict)
    interruptions: dict[str, Any] = field(default_factory=dict)
    conversation: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return a serializable snapshot."""

        return {
            "events": list(self.events),
            "sessions": list(self.sessions),
            "intents": list(self.intents),
            "memory": dict(self.memory),
            "voice": dict(self.voice),
            "providers": dict(self.providers),
            "bridge": dict(self.bridge),
            "notifications": list(self.notifications),
            "errors": list(self.errors),
            "system": dict(self.system),
            "performance": dict(self.performance),
            "interruptions": dict(self.interruptions),
            "conversation": dict(self.conversation),
        }
