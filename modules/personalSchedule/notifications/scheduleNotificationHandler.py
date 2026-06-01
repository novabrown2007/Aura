"""Notification bridge for Aura's personal schedule hub."""

from __future__ import annotations


class ScheduleNotificationHandler:
    """Convert schedule lifecycle events into notifications."""

    def __init__(self, context, manager):
        self.context = context
        self.manager = manager
        self.logger = context.logger.getChild("PersonalSchedule.Notifications") if getattr(context, "logger", None) else None

    def notify(self, item, eventName: str, message: str, priority: str = "NORMAL"):
        notificationManager = getattr(self.context, "notificationManager", None)
        if notificationManager is None or not hasattr(notificationManager, "createNotification"):
            return None
        payload = {
            "title": item.title,
            "message": message,
            "priority": priority,
            "category": self._categoryForItem(item),
            "source": "personalSchedule",
            "deliveryMode": "VOICE_AND_UI" if priority in {"HIGH", "CRITICAL", "EMERGENCY"} else "UI_ONLY",
            "requiresAcknowledgement": priority in {"CRITICAL", "EMERGENCY"},
            "interruptAllowed": priority in {"HIGH", "CRITICAL", "EMERGENCY"},
            "persistent": priority in {"HIGH", "CRITICAL", "EMERGENCY"},
            "metadata": {"itemId": item.itemId, "type": getattr(item.type, "value", str(item.type))},
        }
        return notificationManager.createNotification(payload, eventName=eventName)

    @staticmethod
    def _categoryForItem(item) -> str:
        itemType = getattr(item.type, "value", str(item.type)).upper()
        if itemType == "BILL":
            return "WARNING"
        if itemType == "TIMER":
            return "SYSTEM"
        if itemType == "TASK":
            return "REMINDER"
        return "CALENDAR"
