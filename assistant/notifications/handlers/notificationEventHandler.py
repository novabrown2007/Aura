"""Event-bus bridge for Aura notification attention management."""

from __future__ import annotations


class NotificationEventHandler:
    """Subscribe to domain events and convert them into notifications."""

    events = (
        "motion.detected",
        "door.opened",
        "timer.completed",
        "email.received",
        "smoke.detected",
        "water.leak.detected",
        "conversation.started",
        "conversation.active",
        "interruption.completed",
    )

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager or getattr(context, "notificationManager", None)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Notifications.Events") if logger else None
        self.subscribed = False

    def subscribe(self):
        """Subscribe to runtime events."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or self.subscribed:
            return
        for eventName in self.events:
            try:
                eventManager.subscribe(eventName, self.handleEvent)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Notification subscription failed for {eventName}: {error}")
        self.subscribed = True

    def unsubscribe(self):
        """Remove runtime event subscriptions."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or not self.subscribed:
            return
        for eventName in self.events:
            try:
                eventManager.unsubscribe(eventName, self.handleEvent)
            except Exception:
                pass
        self.subscribed = False

    def handleEvent(self, event):
        """Convert one incoming event into a notification action."""

        manager = self.manager or getattr(self.context, "notificationManager", None)
        if manager is None:
            return
        try:
            manager.handleEvent(event)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Notification event handling failed: {error}")
