"""Recurrence helpers for Aura's personal schedule hub."""

from __future__ import annotations

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule


class RecurrenceManager:
    """Resolve recurrence rules for schedule items."""

    def nextOccurrence(self, rule: RecurrenceRule | None, afterValue: str, anchorValue: str | None = None) -> str | None:
        if rule is None:
            return None
        return rule.nextOccurrence(afterValue, anchorValue)
