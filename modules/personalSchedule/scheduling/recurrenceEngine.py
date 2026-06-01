"""Recurrence helpers for Aura's unified personal schedule hub."""

from __future__ import annotations

from datetime import datetime

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule


class RecurrenceEngine:
    """Compute the next occurrence for recurring schedule items."""

    def nextOccurrence(self, rule: RecurrenceRule | None, afterValue: str, anchorValue: str | None = None) -> str | None:
        if rule is None:
            return None
        return rule.nextOccurrence(afterValue, anchorValue)

    @staticmethod
    def normalizeTimestamp(value: str | None) -> str:
        if not value:
            return datetime.utcnow().isoformat(timespec="seconds")
        try:
            return datetime.fromisoformat(str(value).replace("Z", "")).isoformat(timespec="seconds")
        except Exception:
            return str(value)
