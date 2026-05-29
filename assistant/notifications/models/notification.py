"""Notification record used by the attention-management layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from assistant.notifications.models.notificationCategory import NotificationCategory
from assistant.notifications.models.notificationDeliveryMode import NotificationDeliveryMode
from assistant.notifications.models.notificationPriority import NotificationPriority


@dataclass
class Notification:
    """A prioritized assistant notification."""

    notificationId: str = ""
    title: str = ""
    message: str = ""
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: NotificationCategory = NotificationCategory.SYSTEM
    timestamp: str = ""
    source: str = ""
    deliveryMode: NotificationDeliveryMode = NotificationDeliveryMode.UI_ONLY
    requiresAcknowledgement: bool = False
    interruptAllowed: bool = False
    persistent: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def fromDict(cls, values: dict[str, Any]):
        """Create a notification from a dictionary payload."""

        return cls(
            notificationId=str(values.get("notificationId") or values.get("notification_id") or ""),
            title=str(values.get("title") or ""),
            message=str(values.get("message") or values.get("content") or ""),
            priority=NotificationPriority.normalize(values.get("priority")),
            category=NotificationCategory.normalize(values.get("category")),
            timestamp=str(values.get("timestamp") or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")),
            source=str(values.get("source") or values.get("source_module") or ""),
            deliveryMode=NotificationDeliveryMode.normalize(values.get("deliveryMode")),
            requiresAcknowledgement=bool(values.get("requiresAcknowledgement", False)),
            interruptAllowed=bool(values.get("interruptAllowed", False)),
            persistent=bool(values.get("persistent", False)),
            metadata=dict(values.get("metadata") or {}),
        )

    def asDict(self) -> dict[str, Any]:
        """Return a serializable notification representation."""

        return {
            "notificationId": self.notificationId,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "category": self.category.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "deliveryMode": self.deliveryMode.value,
            "requiresAcknowledgement": bool(self.requiresAcknowledgement),
            "interruptAllowed": bool(self.interruptAllowed),
            "persistent": bool(self.persistent),
            "metadata": dict(self.metadata),
        }

    def speechText(self) -> str:
        """Return spoken text for voice alerts."""

        if self.title and self.message:
            return f"{self.title}. {self.message}"
        if self.title:
            return self.title
        return self.message
