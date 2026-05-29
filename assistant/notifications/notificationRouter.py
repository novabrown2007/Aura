"""Notification delivery router."""

from __future__ import annotations

from typing import Any

from assistant.notifications.models.notificationDeliveryMode import NotificationDeliveryMode


class NotificationRouter:
    """Route notifications to voice, UI, persistence, and interruption systems."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Notifications.Router") if logger else None

    def route(self, notification, route, notificationContext):
        """Deliver one notification according to the chosen route."""

        delivered = {
            "voice": False,
            "ui": False,
            "interrupted": False,
            "errors": [],
        }

        if route.interrupt:
            interrupted = self._interrupt(notification, route, notificationContext)
            delivered["interrupted"] = bool(interrupted)

        if route.ui:
            self._emit("assistant.notification", notification.asDict())
            delivered["ui"] = True

        if route.voice:
            try:
                voiceManager = getattr(self.context, "voiceManager", None)
                if voiceManager is None:
                    raise RuntimeError("Voice manager is unavailable.")
                voiceManager.speakResponse(notification.speechText())
                delivered["voice"] = True
            except Exception as error:
                delivered["errors"].append(str(error))
                if self.logger:
                    self.logger.warning(f"Notification voice delivery failed: {error}")

        return delivered

    def _interrupt(self, notification, route, notificationContext):
        manager = getattr(self.context, "notificationInterruptionManager", None) or getattr(self.context, "interruptionManager", None)
        if manager is None:
            return False
        return bool(manager.interrupt(notification, route, notificationContext))

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        return eventManager.emit(eventName, payload)
