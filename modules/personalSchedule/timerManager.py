"""Timer helpers for Aura's personal schedule hub."""

from __future__ import annotations

from datetime import datetime, timedelta

from modules.personalSchedule.models.scheduleItem import ScheduleItem
from modules.personalSchedule.models.scheduleItemType import ScheduleItemType


class TimerManager:
    """Create and manage countdown timer schedule items."""

    def __init__(self, manager):
        self.manager = manager

    def createTimer(self, title: str = "", durationSeconds: int = 0, description: str = "", priority: str = "NORMAL", tags=None, metadata=None, source: str = "assistant", requiresAcknowledgement: bool = False, **fields):
        durationSeconds = max(0, int(durationSeconds or 0))
        endTime = (datetime.utcnow() + timedelta(seconds=durationSeconds)).isoformat(timespec="seconds")
        item = ScheduleItem(
            title=str(title or "Timer"),
            description=str(description or ""),
            type=ScheduleItemType.TIMER,
            endTime=endTime,
            priority=str(priority or "NORMAL"),
            tags=list(tags or []),
            metadata={"durationSeconds": durationSeconds, **dict(metadata or {})},
            source=str(source or "assistant"),
            requiresAcknowledgement=bool(requiresAcknowledgement),
        )
        item.metadata.update({key: value for key, value in fields.items() if value is not None})
        return self.manager.saveItem(item)

    def pauseTimer(self, itemId: str):
        return self.manager.pauseTimer(itemId)

    def resumeTimer(self, itemId: str):
        return self.manager.resumeTimer(itemId)

    def completeTimer(self, itemId: str):
        return self.manager.completeTimer(itemId)
