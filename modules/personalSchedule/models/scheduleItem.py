"""Unified schedule item model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from modules.personalSchedule.models.recurrenceRule import RecurrenceRule
from modules.personalSchedule.models.scheduleItemType import ScheduleItemType
from modules.personalSchedule.models.scheduleState import ScheduleState


@dataclass
class ScheduleItem:
    itemId: str = field(default_factory=lambda: uuid4().hex)
    title: str = ""
    description: str = ""
    type: ScheduleItemType = ScheduleItemType.EVENT
    startTime: str = ""
    endTime: str = ""
    dueTime: str = ""
    priority: str = "NORMAL"
    tags: list[str] = field(default_factory=list)
    state: ScheduleState = ScheduleState.PENDING
    recurrenceRule: RecurrenceRule | None = None
    createdAt: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    updatedAt: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    requiresAcknowledgement: bool = False

    def asDict(self) -> dict[str, Any]:
        return {
            "itemId": self.itemId,
            "title": self.title,
            "description": self.description,
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "startTime": self.startTime,
            "endTime": self.endTime,
            "dueTime": self.dueTime,
            "priority": self.priority,
            "tags": list(self.tags or []),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "recurrenceRule": self.recurrenceRule.asDict() if self.recurrenceRule else None,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "metadata": dict(self.metadata or {}),
            "source": self.source,
            "requiresAcknowledgement": bool(self.requiresAcknowledgement),
        }

    @classmethod
    def fromDict(cls, values: dict[str, Any]):
        recurrenceRule = values.get("recurrenceRule") or values.get("recurrence_rule")
        if isinstance(recurrenceRule, str) and recurrenceRule.strip().lower() in {"", "null", "none"}:
            recurrenceRule = None
        if recurrenceRule is not None and not isinstance(recurrenceRule, RecurrenceRule):
            recurrenceRule = RecurrenceRule.fromDict(recurrenceRule)
        return cls(
            itemId=str(values.get("itemId") or values.get("item_id") or uuid4().hex),
            title=str(values.get("title") or ""),
            description=str(values.get("description") or ""),
            type=ScheduleItemType.normalize(values.get("type")),
            startTime=str(values.get("startTime") or values.get("start_time") or ""),
            endTime=str(values.get("endTime") or values.get("end_time") or ""),
            dueTime=str(values.get("dueTime") or values.get("due_time") or ""),
            priority=str(values.get("priority") or "NORMAL"),
            tags=list(values.get("tags") or []),
            state=ScheduleState.normalize(values.get("state")),
            recurrenceRule=recurrenceRule,
            createdAt=str(values.get("createdAt") or values.get("created_at") or datetime.utcnow().isoformat(timespec="seconds")),
            updatedAt=str(values.get("updatedAt") or values.get("updated_at") or datetime.utcnow().isoformat(timespec="seconds")),
            metadata=dict(values.get("metadata") or {}),
            source=str(values.get("source") or ""),
            requiresAcknowledgement=bool(values.get("requiresAcknowledgement", values.get("requires_acknowledgement", False))),
        )
