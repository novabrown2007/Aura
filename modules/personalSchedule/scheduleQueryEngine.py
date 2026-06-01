"""Query helpers for Aura's personal schedule hub."""

from __future__ import annotations

from datetime import datetime, timedelta

from modules.personalSchedule.models.scheduleItemType import ScheduleItemType
from modules.personalSchedule.models.scheduleState import ScheduleState


class ScheduleQueryEngine:
    """Compute filtered and grouped views over schedule items."""

    def __init__(self, manager):
        self.manager = manager

    def getTodaysSchedule(self):
        today = datetime.utcnow().date().isoformat()
        items = [item for item in self.manager.listScheduleItems() if self._itemDate(item).startswith(today)]
        return self._buildSummary("Today", items)

    def getUpcomingSchedule(self, limit: int = 10):
        items = self.manager.listScheduleItems()
        upcoming = [item for item in items if item.state not in {ScheduleState.COMPLETED, ScheduleState.CANCELLED, ScheduleState.ARCHIVED}]
        return self._buildSummary("Upcoming", upcoming[: int(limit)])

    def getUpcomingReminders(self, limit: int = 10):
        items = [item for item in self.manager.listScheduleItems(itemType=ScheduleItemType.REMINDER)]
        return self._buildSummary("Reminders", items[: int(limit)])

    def getOverdueTasks(self, limit: int = 10):
        items = [item for item in self.manager.listScheduleItems(itemType=ScheduleItemType.TASK)]
        overdue = [item for item in items if item.state in {ScheduleState.OVERDUE, ScheduleState.MISSED} or self._itemDate(item) < datetime.utcnow().date().isoformat()]
        return self._buildSummary("Overdue tasks", overdue[: int(limit)])

    def search(self, query: str, limit: int = 20):
        items = self.manager.searchSchedule(query, limit=limit)
        return self._buildSummary(f"Search: {query}", items)

    def _buildSummary(self, title: str, items):
        return {
            "title": title,
            "count": len(items),
            "items": [item.asDict() for item in items],
        }

    @staticmethod
    def _itemDate(item):
        value = item.startTime or item.dueTime or item.endTime or item.createdAt
        return str(value or "")[:10]
