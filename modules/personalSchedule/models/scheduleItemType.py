"""Schedule item types for Aura's unified schedule hub."""

from __future__ import annotations

from enum import Enum


class ScheduleItemType(str, Enum):
    EVENT = "EVENT"
    REMINDER = "REMINDER"
    TASK = "TASK"
    MEETING = "MEETING"
    BILL = "BILL"
    ROUTINE = "ROUTINE"
    TIMER = "TIMER"
    DEADLINE = "DEADLINE"

    @classmethod
    def normalize(cls, value) -> "ScheduleItemType":
        if isinstance(value, cls):
            return value
        normalized = str(value or "EVENT").strip().upper()
        if normalized not in cls.__members__:
            return cls.EVENT
        return cls[normalized]

