"""Task helpers for Aura's personal schedule hub."""

from __future__ import annotations

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule
from modules.personalSchedule.models.scheduleItem import ScheduleItem
from modules.personalSchedule.models.scheduleItemType import ScheduleItemType


class TaskManager:
    """Create and update task schedule items."""

    def __init__(self, manager):
        self.manager = manager

    def createTask(self, title: str, dueDate: str = "", description: str = "", priority: str = "NORMAL", tags=None, repeatRule=None, metadata=None, source: str = "assistant", requiresAcknowledgement: bool = False, **fields):
        item = ScheduleItem(
            title=str(title or ""),
            description=str(description or ""),
            type=ScheduleItemType.TASK,
            dueTime=str(dueDate or ""),
            priority=str(priority or "NORMAL"),
            tags=list(tags or []),
            recurrenceRule=repeatRule if isinstance(repeatRule, RecurrenceRule) else RecurrenceRule.fromDict(repeatRule) if repeatRule else None,
            metadata=dict(metadata or {}),
            source=str(source or "assistant"),
            requiresAcknowledgement=bool(requiresAcknowledgement),
        )
        item.metadata.update({key: value for key, value in fields.items() if value is not None})
        return self.manager.saveItem(item)
