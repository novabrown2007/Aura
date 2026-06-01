"""Reminder model for Aura's unified schedule hub."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule
from modules.personalSchedule.models.scheduleState import ScheduleState


@dataclass
class Reminder:
    """Reminder-specific view over a schedule item."""

    reminderId: str = ""
    title: str = ""
    description: str = ""
    dueTime: str = ""
    priority: str = "NORMAL"
    tags: list[str] = field(default_factory=list)
    state: ScheduleState = ScheduleState.PENDING
    recurrenceRule: RecurrenceRule | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return a serializable reminder payload."""

        return {
            "reminderId": self.reminderId,
            "title": self.title,
            "description": self.description,
            "dueTime": self.dueTime,
            "priority": self.priority,
            "tags": list(self.tags or []),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "recurrenceRule": self.recurrenceRule.asDict() if self.recurrenceRule else None,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        """Create a reminder from a dictionary payload."""

        values = dict(values or {})
        reminderRule = values.get("recurrenceRule") or values.get("recurrence_rule")
        return cls(
            reminderId=str(values.get("reminderId") or values.get("reminder_id") or values.get("itemId") or values.get("item_id") or ""),
            title=str(values.get("title") or ""),
            description=str(values.get("description") or values.get("content") or ""),
            dueTime=str(values.get("dueTime") or values.get("due_time") or values.get("remindAt") or values.get("remind_at") or ""),
            priority=str(values.get("priority") or "NORMAL"),
            tags=list(values.get("tags") or []),
            state=ScheduleState.normalize(values.get("state")),
            recurrenceRule=RecurrenceRule.fromDict(reminderRule) if reminderRule else None,
            metadata=dict(values.get("metadata") or {}),
        )

    def toScheduleTime(self) -> str:
        """Return the best canonical timestamp for the reminder."""

        if self.dueTime:
            return self.dueTime
        return datetime.utcnow().isoformat(timespec="seconds")
