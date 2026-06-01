"""Schedule item engine for Aura's unified personal schedule hub."""

from __future__ import annotations

from datetime import datetime

from modules.personalSchedule.models.scheduleState import ScheduleState


class ScheduleEngine:
    """Apply lifecycle transitions to schedule items."""

    def markDueState(self, item, nowIso: str | None = None):
        nowIso = nowIso or datetime.utcnow().isoformat(timespec="seconds")
        dueField = self._dueField(item)
        dueValue = getattr(item, dueField, "") if dueField else ""
        if not dueValue:
            return ScheduleState.PENDING
        if str(dueValue) <= nowIso and item.state in {ScheduleState.PENDING, ScheduleState.ACTIVE, ScheduleState.SNOOZED}:
            return ScheduleState.OVERDUE if item.type.value in {"TASK", "BILL", "DEADLINE"} else ScheduleState.ACTIVE
        return item.state

    @staticmethod
    def _dueField(item) -> str:
        itemType = getattr(item.type, "value", str(getattr(item, "type", ""))).upper()
        if itemType == "TIMER":
            return "endTime"
        if itemType in {"TASK", "BILL", "DEADLINE"}:
            return "dueTime"
        return "startTime"
