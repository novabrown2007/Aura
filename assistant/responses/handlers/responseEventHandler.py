"""Event bus bridge for structured assistant responses."""

from __future__ import annotations


class ResponseEventHandler:
    """Track response-adjacent events and update cached context."""

    eventNames = (
        "intent.generated",
        "intent.executed",
        "notification.created",
        "conversation.updated",
        "memory.retrieved",
        "response.created",
        "response.validated",
        "response.routed",
        "response.delivered",
        "response.failed",
    )

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager or getattr(context, "responseManager", None)
        self._subscribed = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Events") if logger else None

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
                    self.logger.warning(f"Response event subscription failed for {eventName}: {error}")
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
        manager = self.manager or getattr(self.context, "responseManager", None)
        if manager is None or not hasattr(manager, "contextManager"):
            return
        try:
            manager.contextManager.updateFromEvent(name, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Response event handling failed for {name}: {error}")
