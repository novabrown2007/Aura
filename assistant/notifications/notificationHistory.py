"""Notification delivery history tracking."""

from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any


class NotificationHistory:
    """Track notification lifecycle results."""

    def __init__(self, maxEntries: int = 500):
        self.maxEntries = int(maxEntries)
        self.entries = deque(maxlen=self.maxEntries)
        self._lock = RLock()

    def record(self, eventName: str, notification: dict[str, Any], details: dict[str, Any] | None = None):
        """Store one lifecycle event."""

        entry = {
            "event": str(eventName),
            "notificationId": str(notification.get("notificationId") or ""),
            "priority": str(notification.get("priority") or ""),
            "category": str(notification.get("category") or ""),
            "title": str(notification.get("title") or ""),
            "timestamp": str(notification.get("timestamp") or ""),
            "details": dict(details or {}),
        }
        with self._lock:
            self.entries.append(entry)
        return entry

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable history snapshot."""

        with self._lock:
            return {
                "count": len(self.entries),
                "entries": list(self.entries),
            }
