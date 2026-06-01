"""Assistant status model for the Windows desktop layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class AssistantStatus:
    """Current visible assistant state for the desktop bubble."""

    state: str = "IDLE"
    message: str = ""
    provider: str = ""
    connected: bool = True
    muted: bool = False
    listening: bool = False
    processing: bool = False
    responding: bool = False
    notifying: bool = False
    lastUpdated: str = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "message": self.message,
            "provider": self.provider,
            "connected": self.connected,
            "muted": self.muted,
            "listening": self.listening,
            "processing": self.processing,
            "responding": self.responding,
            "notifying": self.notifying,
            "lastUpdated": self.lastUpdated,
            "metadata": dict(self.metadata),
        }

