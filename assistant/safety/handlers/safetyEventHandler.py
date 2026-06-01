"""Event bus bridge for execution governance."""

from __future__ import annotations


class SafetyEventHandler:
    """Subscribe to execution-related runtime events."""

    eventNames = (
        "action.requested",
        "automation.triggered",
        "module.action.executed",
        "confirmation.received",
    )

    def __init__(self, context=None, safetyManager=None):
        self.context = context
        self.safetyManager = safetyManager or getattr(context, "safetyManager", None)
        self._subscribed = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Safety.Events") if logger else None

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
                    self.logger.warning(f"Safety event subscription failed for {eventName}: {error}")
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
        name = getattr(event, "name", "")
        payload = getattr(event, "data", {}) or {}
        manager = self.safetyManager or getattr(self.context, "safetyManager", None)
        if manager is None:
            return
        if name == "confirmation.received":
            if payload.get("origin") == "safety_manager":
                return
            confirmation = payload.get("requestId") or payload.get("confirmationId")
            if confirmation is not None:
                try:
                    manager.confirm(str(confirmation), approved=bool(payload.get("approved", True)))
                except Exception:
                    pass
