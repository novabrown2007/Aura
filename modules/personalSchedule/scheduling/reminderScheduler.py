"""Reminder scheduling helpers for Aura's unified personal schedule hub."""

from __future__ import annotations

from datetime import datetime


class ReminderScheduler:
    """Normalize reminder timestamps."""

    @staticmethod
    def normalizeReminderTime(value: str | None) -> str:
        if not value:
            return datetime.utcnow().isoformat(timespec="seconds")
        return str(value)
