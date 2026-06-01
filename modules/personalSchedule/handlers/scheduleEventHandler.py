"""Event bus bridge for Aura's personal schedule hub."""

from __future__ import annotations


class ScheduleEventHandler:
    """Subscribe schedule lifecycle hooks to the event bus."""

    DEFAULT_EVENTS = (
        "schedule.tick",
        "system.started",
        "conversation.started",
        "notification.acknowledged",
    )

    def __init__(self, context, manager):
        self.context = context
        self.manager = manager
        self.logger = context.logger.getChild("PersonalSchedule.Events") if getattr(context, "logger", None) else None
        self._subscribed = False

    def subscribe(self):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or self._subscribed:
            return
        for eventName in self.DEFAULT_EVENTS:
            eventManager.subscribe(eventName, self.handleEvent)
        self._subscribed = True

    def unsubscribe(self):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or not self._subscribed:
            return
        for eventName in self.DEFAULT_EVENTS:
            eventManager.unsubscribe(eventName, self.handleEvent)
        self._subscribed = False

    def handleEvent(self, event):
        eventName = getattr(event, "name", "")
        if eventName == "schedule.tick":
            return self.manager.processTick(getattr(event, "data", {}) or {})
        if eventName in {"system.started", "conversation.started", "notification.acknowledged"}:
            return self.manager.refreshContext()
        return None
