"""Spotify queue manager placeholder for future queue orchestration."""

from __future__ import annotations


class SpotifyQueueManager:
    """Maintain a deterministic in-memory play queue."""

    def __init__(self):
        self.queue: list[dict[str, object]] = []

    def enqueue(self, item: dict[str, object]):
        self.queue.append(dict(item or {}))
        return list(self.queue)

    def dequeue(self):
        if not self.queue:
            return None
        return self.queue.pop(0)

    def clear(self):
        self.queue.clear()
        return []

    def listQueue(self):
        return list(self.queue)
