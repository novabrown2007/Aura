"""Priority-aware notification queue."""

from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any

from assistant.notifications.models.notificationPriority import NotificationPriority


class NotificationQueue:
    """Queue notification objects with priority ordering."""

    def __init__(self, maxSize: int = 50):
        self.maxSize = int(maxSize)
        self._lock = RLock()
        self._queue: list[dict[str, Any]] = []

    def enqueue(self, notification: dict[str, Any]):
        """Insert a notification in priority order."""

        with self._lock:
            self._queue.append(dict(notification))
            self._queue.sort(
                key=lambda item: (
                    -NotificationPriority.rank(item.get("priority")),
                    str(item.get("timestamp") or ""),
                    str(item.get("notificationId") or ""),
                )
            )
            overflow = None
            if len(self._queue) > self.maxSize:
                overflow = self._queue.pop(-1)
            return overflow

    def dequeue(self):
        """Return the next notification in delivery order."""

        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop(0)

    def peek(self):
        """Return the next queued notification without removing it."""

        with self._lock:
            return dict(self._queue[0]) if self._queue else None

    def remove(self, notificationId: str):
        """Remove one notification from the queue."""

        with self._lock:
            before = len(self._queue)
            self._queue = [item for item in self._queue if str(item.get("notificationId") or "") != str(notificationId)]
            return before != len(self._queue)

    def clear(self):
        """Empty the queue."""

        with self._lock:
            self._queue.clear()

    def snapshot(self) -> dict[str, Any]:
        """Return a serializable queue snapshot."""

        with self._lock:
            return {
                "count": len(self._queue),
                "maxSize": self.maxSize,
                "items": [dict(item) for item in self._queue],
            }
