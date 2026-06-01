"""Bridge runtime events into execution state refreshes."""

from __future__ import annotations


class ExecutionEventHandler:
    """Subscribe the execution manager to runtime events."""

    eventNames = (
        "intent.resolved",
        "confirmation.received",
        "automation.triggered",
        "module.loaded",
    )

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager
        self._subscribed = False

    def subscribe(self):
        if self._subscribed:
            return
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return
        for name in self.eventNames:
            try:
                eventBus.subscribe(name, self.handleEvent)
            except Exception:
                pass
        self._subscribed = True

    def unsubscribe(self):
        if not self._subscribed:
            return
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return
        for name in self.eventNames:
            try:
                eventBus.unsubscribe(name, self.handleEvent)
            except Exception:
                pass
        self._subscribed = False

    def handleEvent(self, event):
        if self.manager is None:
            return None
        name = getattr(event, "name", "") if not isinstance(event, dict) else event.get("name", "")
        payload = getattr(event, "data", {}) if not isinstance(event, dict) else event.get("data", {}) or {}
        if name == "module.loaded":
            return self.manager.refreshRegistry()
        if name == "intent.resolved":
            return self.manager.handleResolvedIntent(payload)
        if name == "confirmation.received":
            return self.manager.handleConfirmation(payload)
        if name == "automation.triggered":
            return self.manager.handleAutomationTriggered(payload)
