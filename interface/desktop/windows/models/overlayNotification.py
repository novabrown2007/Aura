"""Desktop notification model for Aura's Windows overlay."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class OverlayNotification:
    """One desktop notification surfaced through the overlay layer."""

    notificationId: str = field(default_factory=lambda: uuid4().hex)
    title: str = ""
    message: str = ""
    priority: str = "NORMAL"
    source: str = ""
    timestamp: str = field(default_factory=_now)
    persistent: bool = False
    requiresAcknowledgement: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "notificationId": self.notificationId,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "source": self.source,
            "timestamp": self.timestamp,
            "persistent": self.persistent,
            "requiresAcknowledgement": self.requiresAcknowledgement,
            "metadata": dict(self.metadata),
        }

