"""Reminder helpers for Aura's personal schedule hub."""

from __future__ import annotations

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule
from modules.personalSchedule.models.scheduleItem import ScheduleItem
from modules.personalSchedule.models.scheduleItemType import ScheduleItemType


class ReminderManager:
    """Create and update reminder schedule items."""

    def __init__(self, manager):
        self.manager = manager

    def createReminder(self, title: str, dueTime: str, description: str = "", priority: str = "NORMAL", tags=None, recurrenceRule=None, metadata=None, source: str = "assistant", requiresAcknowledgement: bool = False, **fields):
        item = ScheduleItem(
            title=str(title or ""),
            description=str(description or ""),
            type=ScheduleItemType.REMINDER,
            dueTime=str(dueTime or ""),
            priority=str(priority or "NORMAL"),
            tags=list(tags or []),
            recurrenceRule=recurrenceRule if isinstance(recurrenceRule, RecurrenceRule) else RecurrenceRule.fromDict(recurrenceRule) if recurrenceRule else None,
            metadata=dict(metadata or {}),
            source=str(source or "assistant"),
            requiresAcknowledgement=bool(requiresAcknowledgement),
        )
        item.metadata.update({key: value for key, value in fields.items() if value is not None})
        return self.manager.saveItem(item)
