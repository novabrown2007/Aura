"""Event bus glue for the email module."""

from __future__ import annotations


class EmailEventHandler:
    """Subscribe email module services to runtime events."""

    eventNames = (
        "system.started",
        "schedule.tick",
        "email.sync.requested",
        "notification.acknowledged",
        "conversation.confirmation.received",
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
        for eventName in self.eventNames:
            try:
                eventBus.subscribe(eventName, self.handleEvent)
            except Exception:
                pass
        self._subscribed = True

    def unsubscribe(self):
        if not self._subscribed:
            return
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return
        for eventName in self.eventNames:
            try:
                eventBus.unsubscribe(eventName, self.handleEvent)
            except Exception:
                pass
        self._subscribed = False

    def handleEvent(self, event):
        name = getattr(event, "name", "") if not isinstance(event, dict) else event.get("name", "")
        payload = getattr(event, "data", {}) if not isinstance(event, dict) else event.get("data", {}) or {}
        if name == "system.started":
            self.manager.connectAllAccounts()
            self.manager.syncAll()
        elif name == "schedule.tick":
            self.manager.processScheduledEmails()
            self.manager.pollNewMail()
        elif name == "email.sync.requested":
            accountId = str(payload.get("accountId") or "")
            self.manager.sync(accountId or None)
        elif name == "notification.acknowledged":
            self.manager.markNotificationAcknowledged(payload)
        elif name == "conversation.confirmation.received":
            self.manager.handleConfirmation(payload)
