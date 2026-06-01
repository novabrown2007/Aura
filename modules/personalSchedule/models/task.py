"""Task model for Aura's unified schedule hub."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule
from modules.personalSchedule.models.scheduleState import ScheduleState


@dataclass
class Task:
    """Task-specific view over a schedule item."""

    taskId: str = ""
    title: str = ""
    description: str = ""
    dueDate: str = ""
    priority: str = "NORMAL"
    completed: bool = False
    tags: list[str] = field(default_factory=list)
    repeatRule: RecurrenceRule | dict[str, Any] | None = field(default_factory=dict)
    state: ScheduleState = ScheduleState.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        """Return a serializable task payload."""

        repeatRule = self.repeatRule.asDict() if isinstance(self.repeatRule, RecurrenceRule) else dict(self.repeatRule or {})
        return {
            "taskId": self.taskId,
            "title": self.title,
            "description": self.description,
            "dueDate": self.dueDate,
            "priority": self.priority,
            "completed": bool(self.completed),
            "tags": list(self.tags or []),
            "repeatRule": repeatRule,
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any] | None):
        """Create a task from a dictionary payload."""

        values = dict(values or {})
        repeatRule = values.get("repeatRule") or values.get("repeat_rule")
        return cls(
            taskId=str(values.get("taskId") or values.get("task_id") or values.get("itemId") or values.get("item_id") or ""),
            title=str(values.get("title") or ""),
            description=str(values.get("description") or ""),
            dueDate=str(values.get("dueDate") or values.get("due_date") or values.get("dueTime") or values.get("due_time") or ""),
            priority=str(values.get("priority") or "NORMAL"),
            completed=bool(values.get("completed", False)),
            tags=list(values.get("tags") or []),
            repeatRule=RecurrenceRule.fromDict(repeatRule) if repeatRule else {},
            state=ScheduleState.normalize(values.get("state")),
            metadata=dict(values.get("metadata") or {}),
        )
