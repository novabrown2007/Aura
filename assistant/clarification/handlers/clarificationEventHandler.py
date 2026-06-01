"""Event bridge for clarification state."""

from __future__ import annotations


class ClarificationEventHandler:
    """Track clarification-adjacent runtime events."""

    eventNames = (
        "intent.resolved",
        "execution.validation.failed",
        "execution.pending",
        "conversation.updated",
        "clarification.requested",
        "clarification.resolved",
        "clarification.timed_out",
        "clarification.cancelled",
        "clarification.failed",
    )

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager or getattr(context, "clarificationManager", None)
        self._subscribed = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Events") if logger else None

    def subscribe(self):
        if self._subscribed:
            return
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        for eventName in self.eventNames:
            try:
                eventManager.subscribe(eventName, self.handleEvent)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Clarification event subscription failed for {eventName}: {error}")
        self._subscribed = True

    def unsubscribe(self):
        if not self._subscribed:
            return
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        for eventName in self.eventNames:
            try:
                eventManager.unsubscribe(eventName, self.handleEvent)
            except Exception:
                pass
        self._subscribed = False

    def handleEvent(self, event):
        payload = getattr(event, "data", {}) or {}
        name = getattr(event, "name", "")
        manager = self.manager or getattr(self.context, "clarificationManager", None)
        if manager is None:
            return
        contextManager = getattr(manager, "contextManager", None)
        if contextManager is None or not hasattr(contextManager, "updateFromEvent"):
            return
        try:
            contextManager.updateFromEvent(name, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Clarification event handling failed for {name}: {error}")
