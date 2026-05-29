"""Event-bus integration for Aura personality systems."""

from __future__ import annotations


class PersonalityEventHandler:
    """Listen to runtime events and update personality context."""

    events = (
        "conversation.started",
        "response.generated",
        "task.completed",
        "task_completed",
        "session.started",
        "session.created",
        "notification.received",
        "assistant.notification",
    )

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager or getattr(context, "personalityManager", None)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Personality.Events") if logger else None
        self.subscribed = False

    def subscribe(self):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or self.subscribed:
            return
        for eventName in self.events:
            try:
                eventManager.subscribe(eventName, self.handleEvent)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Personality subscription failed for {eventName}: {error}")
        self.subscribed = True

    def handleEvent(self, event):
        manager = self.manager or getattr(self.context, "personalityManager", None)
        if manager is None:
            return
        name = getattr(event, "name", "")
        payload = getattr(event, "data", {}) or {}
        try:
            manager.interactionContext.recordActivity(name, payload)
        except Exception as error:
            if self.logger:
                self.logger.debug(f"Personality event handling failed for {name}: {error}")

