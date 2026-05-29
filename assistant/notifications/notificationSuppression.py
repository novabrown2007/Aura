"""Notification suppression rules and cooldown tracking."""

from __future__ import annotations

from collections import deque
from threading import RLock
from time import time
from typing import Any

from assistant.notifications.models.notificationPriority import NotificationPriority


class NotificationSuppression:
    """Suppress repetitive or noisy notifications."""

    def __init__(self, cooldownSeconds: int = 30, maxHistory: int = 200):
        self.cooldownSeconds = int(cooldownSeconds)
        self.maxHistory = int(maxHistory)
        self._lock = RLock()
        self._lastSeen: dict[str, float] = {}
        self.entries = deque(maxlen=self.maxHistory)

    def shouldSuppress(self, notification: dict[str, Any], context: dict[str, Any] | None = None):
        """Return whether a notification should be suppressed."""

        context = context or {}
        priority = NotificationPriority.normalize(notification.get("priority"))
        if priority in {NotificationPriority.CRITICAL, NotificationPriority.EMERGENCY}:
            return False, ""

        fingerprint = self._fingerprint(notification)
        now = time()
        with self._lock:
            lastSeen = self._lastSeen.get(fingerprint)
            if lastSeen is not None and (now - lastSeen) < float(self.cooldownSeconds):
                return True, "cooldown"
            self._lastSeen[fingerprint] = now
            self.entries.append(
                {
                    "timestamp": now,
                    "fingerprint": fingerprint,
                    "priority": priority.value,
                    "title": str(notification.get("title") or ""),
                }
            )
        return False, ""

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable suppression snapshot."""

        with self._lock:
            return {
                "cooldownSeconds": self.cooldownSeconds,
                "entries": list(self.entries),
            }

    @staticmethod
    def _fingerprint(notification: dict[str, Any]) -> str:
        parts = [
            str(notification.get("source") or ""),
            str(notification.get("category") or ""),
            str(notification.get("title") or ""),
            str(notification.get("message") or ""),
        ]
        return "|".join(part.strip().lower() for part in parts)
