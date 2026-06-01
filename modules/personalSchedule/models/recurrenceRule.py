"""Recurrence rules for unified schedule items."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class RecurrenceRule:
    frequency: str = "daily"
    interval: int = 1
    byWeekdays: tuple[int, ...] = ()
    byMonthDay: int | None = None
    until: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "frequency": self.frequency,
            "interval": int(self.interval),
            "byWeekdays": list(self.byWeekdays),
            "byMonthDay": self.byMonthDay,
            "until": self.until,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        if isinstance(values, cls):
            return values
        if isinstance(values, str):
            try:
                values = json.loads(values)
            except Exception:
                values = {}
        if not isinstance(values, dict):
            values = {}
        return cls(
            frequency=str(values.get("frequency") or "daily").lower(),
            interval=max(1, int(values.get("interval") or 1)),
            byWeekdays=tuple(int(day) for day in values.get("byWeekdays") or values.get("by_weekdays") or ()),
            byMonthDay=cls._optionalInt(values.get("byMonthDay") or values.get("by_month_day")),
            until=str(values.get("until") or ""),
            metadata=dict(values.get("metadata") or {}),
        )

    def nextOccurrence(self, afterValue: str, anchorValue: str | None = None) -> str | None:
        """Return the next occurrence after the supplied timestamp."""

        try:
            after = datetime.fromisoformat(str(afterValue).replace("Z", ""))
        except Exception:
            return None
        anchor = after
        if anchorValue:
            try:
                anchor = datetime.fromisoformat(str(anchorValue).replace("Z", ""))
            except Exception:
                anchor = after

        if self.frequency == "daily":
            return (after + timedelta(days=self.interval)).isoformat(timespec="seconds")
        if self.frequency == "weekly":
            return (after + timedelta(weeks=self.interval)).isoformat(timespec="seconds")
        if self.frequency == "monthly":
            return self._addMonths(after, self.interval).isoformat(timespec="seconds")
        if self.frequency == "yearly":
            return self._addYears(after, self.interval).isoformat(timespec="seconds")
        if self.frequency == "interval":
            return (after + timedelta(seconds=self.interval)).isoformat(timespec="seconds")
        return None

    @staticmethod
    def _optionalInt(value):
        try:
            return int(value) if value is not None and str(value).strip() != "" else None
        except Exception:
            return None

    @staticmethod
    def _addMonths(value: datetime, months: int) -> datetime:
        month = value.month - 1 + months
        year = value.year + month // 12
        month = month % 12 + 1
        day = min(value.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return value.replace(year=year, month=month, day=day)

    @staticmethod
    def _addYears(value: datetime, years: int) -> datetime:
        try:
            return value.replace(year=value.year + years)
        except ValueError:
            return value.replace(month=2, day=28, year=value.year + years)
