"""Notification payload attached to structured assistant responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResponseNotification:
    """Notification routed alongside an assistant response."""

    notificationId: str = ""
    title: str = ""
    message: str = ""
    priority: str = "NORMAL"
    category: str = "SYSTEM"
    deliveryMode: str = "UI_ONLY"
    persistent: bool = False
    requiresAcknowledgement: bool = False
    interruptAllowed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "notificationId": self.notificationId,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "category": self.category,
            "deliveryMode": self.deliveryMode,
            "persistent": bool(self.persistent),
            "requiresAcknowledgement": bool(self.requiresAcknowledgement),
            "interruptAllowed": bool(self.interruptAllowed),
            "metadata": dict(self.metadata or {}),
        }
