"""Email notification orchestration."""

from __future__ import annotations

from typing import Any


class EmailNotificationManager:
    """Surface email activity through Aura's notification system."""

    def __init__(self, context=None):
        self.context = context
        self.seenMessages: set[str] = set()
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Notifications") if getattr(context, "logger", None) else None

    def notifyMessage(self, message: dict[str, Any], force: bool = False):
        messageId = str(message.get("messageId") or "")
        if not messageId:
            return None
        if not force and messageId in self.seenMessages:
            return None
        self.seenMessages.add(messageId)
        notification = {
            "title": self._title(message),
            "message": self._message(message),
            "priority": self._priority(message),
            "category": "EMAIL",
            "source": "email",
            "metadata": {
                "accountId": message.get("accountId"),
                "messageId": messageId,
                "threadId": message.get("threadId", ""),
            },
        }
        manager = getattr(self.context, "notificationManager", None)
        if manager is not None and hasattr(manager, "createNotification"):
            try:
                return manager.createNotification(notification, eventName="email.received")
            except Exception:
                return None
        return notification

    def snapshot(self):
        return {
            "available": True,
            "enabled": bool(self._configValue("email.emailNotificationsEnabled", True)),
            "seenCount": len(self.seenMessages),
        }

    def _priority(self, message: dict[str, Any]):
        subject = str(message.get("subject") or "").lower()
        sender = str(message.get("sender") or "").lower()
        if any(term in subject or term in sender for term in ("security", "urgent", "landlord", "bank", "alert")):
            return "HIGH"
        if bool(message.get("isImportant", False)):
            return "HIGH"
        if any(term in subject for term in ("newsletter", "promotion", "promo")):
            return "LOW"
        return "NORMAL"

    def _title(self, message: dict[str, Any]):
        sender = str(message.get("sender") or "Unknown sender")
        subject = str(message.get("subject") or "New email")
        return f"{sender}: {subject}"

    def _message(self, message: dict[str, Any]):
        snippet = str(message.get("snippet") or message.get("body") or "")
        return snippet[:180]

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
