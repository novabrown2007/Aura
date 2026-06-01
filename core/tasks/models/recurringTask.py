"""Recurring job definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4


@dataclass
class RecurringTask:
    """Describe a simple recurring schedule."""

    recurringTaskId: str = field(default_factory=lambda: uuid4().hex)
    taskName: str = ""
    intervalSeconds: float = 60.0
    nextRunAt: str = ""
    enabled: bool = True
    metadata: dict = field(default_factory=dict)

    def computeNextRun(self, base: datetime | None = None) -> str:
        base = base or datetime.utcnow()
        return (base + timedelta(seconds=float(self.intervalSeconds))).isoformat(timespec="seconds")

    def asDict(self) -> dict:
        return {
            "recurringTaskId": self.recurringTaskId,
            "taskName": self.taskName,
            "intervalSeconds": float(self.intervalSeconds),
            "nextRunAt": self.nextRunAt,
            "enabled": bool(self.enabled),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def fromDict(cls, data: dict | None):
        data = dict(data or {})
        return cls(
            recurringTaskId=str(data.get("recurringTaskId") or uuid4().hex),
            taskName=str(data.get("taskName") or ""),
            intervalSeconds=float(data.get("intervalSeconds") or 60.0),
            nextRunAt=str(data.get("nextRunAt") or ""),
            enabled=bool(data.get("enabled", True)),
            metadata=dict(data.get("metadata") or {}),
        )
