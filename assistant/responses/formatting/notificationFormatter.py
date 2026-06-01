"""Notification formatting for structured assistant responses."""

from __future__ import annotations


class NotificationFormatter:
    """Prepare notification text for assistant delivery."""

    @staticmethod
    def format(title: str, message: str) -> dict[str, str]:
        return {
            "title": str(title or "").strip(),
            "message": str(message or "").strip(),
        }
