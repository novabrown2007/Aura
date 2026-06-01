"""Lifecycle states for schedule items."""

from __future__ import annotations

from enum import Enum


class ScheduleState(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    MISSED = "MISSED"
    OVERDUE = "OVERDUE"
    SNOOZED = "SNOOZED"
    ARCHIVED = "ARCHIVED"

    @classmethod
    def normalize(cls, value) -> "ScheduleState":
        if isinstance(value, cls):
            return value
        normalized = str(value or "PENDING").strip().upper()
        if normalized not in cls.__members__:
            return cls.PENDING
        return cls[normalized]

