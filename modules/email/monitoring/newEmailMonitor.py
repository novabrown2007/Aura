"""New email detection and notification monitor."""

from __future__ import annotations


class NewEmailMonitor:
    """Detect new inbox items and surface them as notifications."""

    def __init__(self, context=None, inboxManager=None, notificationManager=None):
        self.context = context
        self.inboxManager = inboxManager
        self.notificationManager = notificationManager
        self.seen: set[tuple[str, str]] = set()

    def poll(self):
        detections = []
        if self.inboxManager is None or self.inboxManager.connectionManager is None or self.inboxManager.connectionManager.accountManager is None:
            return detections
        for account in self.inboxManager.connectionManager.accountManager.accounts.values():
            inbox = self.inboxManager.syncAccount(account.accountId)
            for message in inbox:
                key = (str(message.get("accountId") or account.accountId), str(message.get("messageId") or ""))
                if key in self.seen:
                    continue
                self.seen.add(key)
                detections.append(message)
                if self.notificationManager is not None:
                    self.notificationManager.notifyMessage(message)
                self._emit("email.received", message)
        return detections

    def _emit(self, name: str, payload: dict):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None
