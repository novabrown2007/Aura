"""Windows desktop notification coordinator for Aura."""

from __future__ import annotations

from typing import Any

from assistant.notifications.models import Notification as AssistantNotification
from assistant.notifications.models import NotificationPriority
from interface.desktop.windows.models import OverlayNotification
from interface.desktop.windows.notifications.notificationPopup import NotificationPopup
from interface.desktop.windows.notifications.notificationStack import NotificationStack


class DesktopNotificationManager:
    """Display assistant notifications as lightweight Windows popups."""

    def __init__(self, context=None, root=None, overlayStateManager=None):
        self.context = context
        self.root = root
        self.overlayStateManager = overlayStateManager
        self.stack = NotificationStack(context)
        self.enabled = bool(self._getConfigValue("overlayNotificationsEnabled", True))
        self.notifications = []
        self._subscribed = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.Notifications") if logger else None

    def start(self):
        self._subscribed = True

    def shutdown(self):
        for popup in list(self.stack.popups):
            try:
                popup.dismiss()
            except Exception:
                pass
        self.stack.popups.clear()

    def showNotification(self, notification: AssistantNotification | OverlayNotification | dict[str, Any]):
        overlayNotification = self._normalize(notification)
        self.notifications.append(overlayNotification.asDict())
        if self.overlayStateManager is not None:
            self.overlayStateManager.setNotificationCount(len(self.notifications))
        if not self.enabled or self.root is None:
            return overlayNotification

        popup = NotificationPopup(self.context, self.root, overlayNotification, onDismiss=self._onPopupDismissed)
        popup.show()
        self.stack.add(popup)
        if self.logger:
            self.logger.info(f"Desktop notification shown: {overlayNotification.title}")
        return overlayNotification

    def snapshot(self) -> dict[str, Any]:
        return {
            "available": True,
            "enabled": self.enabled,
            "active": [popup.notification.asDict() for popup in self.stack.popups],
            "history": list(self.notifications[-50:]),
            "queued": len(self.stack.popups),
        }

    def _onPopupDismissed(self, popup):
        self.stack.remove(popup)

    def _normalize(self, notification):
        if isinstance(notification, OverlayNotification):
            return notification
        if isinstance(notification, AssistantNotification):
            return OverlayNotification(
                notificationId=getattr(notification, "notificationId", "") or getattr(notification, "id", ""),
                title=str(getattr(notification, "title", "") or ""),
                message=str(getattr(notification, "message", "") or ""),
                priority=str(getattr(notification, "priority", "NORMAL") or "NORMAL"),
                source=str(getattr(notification, "source", "") or ""),
                persistent=bool(getattr(notification, "persistent", False)),
                requiresAcknowledgement=bool(getattr(notification, "requiresAcknowledgement", False)),
                metadata=dict(getattr(notification, "metadata", {}) or {}),
            )
        if isinstance(notification, dict):
            return OverlayNotification(
                notificationId=str(notification.get("notificationId") or notification.get("id") or ""),
                title=str(notification.get("title") or ""),
                message=str(notification.get("message") or notification.get("content") or ""),
                priority=str(notification.get("priority") or "NORMAL"),
                source=str(notification.get("source") or ""),
                persistent=bool(notification.get("persistent", False)),
                requiresAcknowledgement=bool(notification.get("requiresAcknowledgement", False)),
                metadata=dict(notification.get("metadata") or {}),
            )
        return OverlayNotification(title="Aura", message=str(notification), priority=NotificationPriority.NORMAL.value)

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
