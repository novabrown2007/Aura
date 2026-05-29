"""Notification escalation tracking."""

from __future__ import annotations

from threading import RLock
from time import time
from typing import Any

from assistant.notifications.models.notificationPriority import NotificationPriority


class EscalationManager:
    """Track and repeat overdue high-priority notifications."""

    def __init__(self):
        self._lock = RLock()
        self.entries: dict[str, dict[str, Any]] = {}

    def register(self, notification: dict[str, Any]):
        """Register one notification for future escalation checks."""

        priority = NotificationPriority.normalize(notification.get("priority"))
        if priority not in {NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY, NotificationPriority.HIGH}:
            return None

        interval = {
            NotificationPriority.HIGH: 45.0,
            NotificationPriority.CRITICAL: 15.0,
            NotificationPriority.EMERGENCY: 10.0,
        }.get(priority, 60.0)
        entry = {
            "notificationId": str(notification.get("notificationId") or ""),
            "priority": priority.value,
            "intervalSeconds": interval,
            "nextAlertAt": time() + interval,
            "acknowledged": False,
            "repeatCount": 0,
        }
        with self._lock:
            self.entries[entry["notificationId"]] = entry
        return entry

    def acknowledge(self, notificationId: str):
        """Mark one notification as acknowledged."""

        with self._lock:
            entry = self.entries.get(str(notificationId))
            if entry is None:
                return False
            entry["acknowledged"] = True
            return True

    def poll(self) -> list[dict[str, Any]]:
        """Return notifications that should be re-alerted now."""

        now = time()
        due = []
        with self._lock:
            for entry in self.entries.values():
                if entry.get("acknowledged"):
                    continue
                if now < float(entry.get("nextAlertAt") or 0.0):
                    continue
                entry["repeatCount"] = int(entry.get("repeatCount", 0)) + 1
                entry["nextAlertAt"] = now + float(entry.get("intervalSeconds") or 30.0)
                due.append(dict(entry))
        return due

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable escalation snapshot."""

        with self._lock:
            return {
                "entries": list(self.entries.values()),
                "activeCount": sum(1 for entry in self.entries.values() if not entry.get("acknowledged")),
            }
