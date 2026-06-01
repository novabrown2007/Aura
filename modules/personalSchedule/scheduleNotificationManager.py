"""Notification bridge for Aura's personal schedule hub."""

from __future__ import annotations

from modules.personalSchedule.notifications.scheduleNotificationHandler import ScheduleNotificationHandler


class ScheduleNotificationManager:
    """Convert schedule lifecycle events into assistant notifications."""

    def __init__(self, context, manager):
        self.context = context
        self.manager = manager
        self.handler = ScheduleNotificationHandler(context, manager)

    def notifyItem(self, item, eventName: str, message: str, priority: str = "NORMAL"):
        return self.handler.notify(item, eventName, message, priority=priority)
