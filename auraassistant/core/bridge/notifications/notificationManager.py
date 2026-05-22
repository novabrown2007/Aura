"""Assistant-facing notification handling for Aura Protocol messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..protocol.auraCategories import AuraCategories


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AssistantNotification:
    """Normalized assistant notification."""

    notificationId: str
    event: str
    location: str = ""
    priority: str = "normal"
    source: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    sessionId: str = ""
    interface: str = ""
    receivedAt: str = field(default_factory=_now)


class NotificationManager:
    """Store and normalize bridge notifications for assistant awareness."""

    def __init__(self, context=None):
        self.context = context
        self.notifications: list[AssistantNotification] = []

    def record(self, message) -> AssistantNotification | None:
        """Record one assistant notification message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_NOTIFICATION:
            return None

        data = getattr(message, "data", {}) or {}
        notification = AssistantNotification(
            notificationId=str(getattr(message, "messageId", "")),
            event=str(data.get("event") or data.get("title") or "notification"),
            location=str(data.get("location") or ""),
            priority=str(data.get("priority") or "normal"),
            source=dict(getattr(message, "source", {}) or {}),
            data=dict(data),
            sessionId=str(getattr(message, "context", {}).get("sessionId", "")),
            interface=str(getattr(message, "context", {}).get("interface", "")),
        )
        self.notifications.append(notification)
        return notification

    def listNotifications(self) -> list[AssistantNotification]:
        """Return recorded notifications in arrival order."""

        return list(self.notifications)

    def clear(self):
        """Clear stored notifications."""

        self.notifications.clear()

