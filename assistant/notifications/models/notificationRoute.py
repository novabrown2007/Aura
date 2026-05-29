"""Notification delivery route model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from assistant.notifications.models.notificationDeliveryMode import NotificationDeliveryMode


@dataclass
class NotificationRoute:
    """Delivery route decision for a notification."""

    deliveryMode: NotificationDeliveryMode = NotificationDeliveryMode.UI_ONLY
    interrupt: bool = False
    voice: bool = False
    ui: bool = True
    persistent: bool = False
    queue: bool = True
    suppressible: bool = True
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return a serializable route decision."""

        return {
            "deliveryMode": self.deliveryMode.value,
            "interrupt": bool(self.interrupt),
            "voice": bool(self.voice),
            "ui": bool(self.ui),
            "persistent": bool(self.persistent),
            "queue": bool(self.queue),
            "suppressible": bool(self.suppressible),
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
