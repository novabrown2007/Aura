"""Notification-aware interruption coordination."""

from __future__ import annotations

from assistant.notifications.models.notificationPriority import NotificationPriority


class InterruptionManager:
    """Decide when notifications may interrupt the current assistant flow."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Notifications.Interruption") if logger else None

    def canInterrupt(self, notification, route, notificationContext) -> bool:
        """Return whether the notification should interrupt the user."""

        priority = NotificationPriority.normalize(notification.priority)
        if priority in {NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY}:
            return True
        return bool(route.interrupt and getattr(notificationContext, "allowVoiceInterruptions", True))

    def interrupt(self, notification, route, notificationContext):
        """Request a runtime interruption when needed."""

        if not self.canInterrupt(notification, route, notificationContext):
            return False

        interruptionManager = getattr(self.context, "interruptionManager", None)
        if interruptionManager is None:
            return False

        try:
            interruptionManager.requestInterruption(
                phrase=notification.title or notification.message,
                source="notification",
                interruptionType=getattr(interruptionManager, "VOICE_INTERRUPT", "VOICE_INTERRUPT"),
                reason=f"notification:{notification.notificationId}",
                metadata={
                    "notificationId": notification.notificationId,
                    "priority": notification.priority.value,
                    "category": notification.category.value,
                },
            )
            return True
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Notification interruption failed: {error}")
            return False
