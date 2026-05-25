"""Handle assistant.notification messages."""

from __future__ import annotations

from ..protocol.auraCategories import AuraCategories


class NotificationHandler:
    """Record assistant-facing notifications and expose them to Aura."""

    def __init__(self, context, notificationManager, stateCache):
        self.context = context
        self.notificationManager = notificationManager
        self.stateCache = stateCache
        self.logger = context.logger.getChild("Bridge.Notification") if getattr(context, "logger", None) else None

    def handle(self, message):
        """Handle one assistant.notification message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_NOTIFICATION:
            return None
        self.stateCache.updateMessage(message)
        notification = self.notificationManager.record(message)
        self._emit(notification)
        return notification

    def _emit(self, notification):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is not None and notification is not None:
            event_manager.emit(
                AuraCategories.ASSISTANT_NOTIFICATION,
                {
                    "event": notification.event,
                    "location": notification.location,
                    "priority": notification.priority,
                    "source": notification.source,
                    "data": notification.data,
                    "sessionId": notification.sessionId,
                    "interface": notification.interface,
                },
            )

