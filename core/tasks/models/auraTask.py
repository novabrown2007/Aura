"""Canonical Aura async task model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from .retryPolicy import RetryPolicy
from .taskPriority import TaskPriority
from .taskState import TaskState
from .recurringTask import RecurringTask


def _utcstamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


@dataclass
class AuraTask:
    """Canonical lightweight task object."""

    taskId: str = field(default_factory=lambda: uuid4().hex)
    taskName: str = ""
    taskType: str = "callable"
    state: str = TaskState.PENDING
    priority: str = TaskPriority.NORMAL
    createdAt: str = field(default_factory=_utcstamp)
    scheduledAt: str = ""
    startedAt: str = ""
    completedAt: str = ""
    retryPolicy: RetryPolicy = field(default_factory=RetryPolicy)
    executionContext: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    attempts: int = 0
    nextRunAt: str = ""
    lastError: str = ""
    result: Any = None
    recurringTask: RecurringTask | None = None
    cancelRequested: bool = False
    runCount: int = 0

    def asDict(self) -> dict[str, Any]:
        return {
            "taskId": self.taskId,
            "taskName": self.taskName,
            "taskType": self.taskType,
            "state": self.state,
            "priority": self.priority,
            "createdAt": self.createdAt,
            "scheduledAt": self.scheduledAt,
            "startedAt": self.startedAt,
            "completedAt": self.completedAt,
            "retryPolicy": self.retryPolicy.asDict() if hasattr(self.retryPolicy, "asDict") else dict(self.retryPolicy or {}),
            "executionContext": dict(self.executionContext or {}),
            "metadata": dict(self.metadata or {}),
            "attempts": int(self.attempts),
            "nextRunAt": self.nextRunAt,
            "lastError": self.lastError,
            "result": self.result,
            "recurringTask": self.recurringTask.asDict() if hasattr(self.recurringTask, "asDict") else None,
            "cancelRequested": bool(self.cancelRequested),
            "runCount": int(self.runCount),
        }

    @classmethod
    def fromDict(cls, data: dict | None):
        data = dict(data or {})
        retry_policy = data.get("retryPolicy")
        recurring_task = data.get("recurringTask")
        return cls(
            taskId=str(data.get("taskId") or uuid4().hex),
            taskName=str(data.get("taskName") or ""),
            taskType=str(data.get("taskType") or "callable"),
            state=str(data.get("state") or TaskState.PENDING),
            priority=str(data.get("priority") or TaskPriority.NORMAL),
            createdAt=str(data.get("createdAt") or _utcstamp()),
            scheduledAt=str(data.get("scheduledAt") or ""),
            startedAt=str(data.get("startedAt") or ""),
            completedAt=str(data.get("completedAt") or ""),
            retryPolicy=retry_policy if isinstance(retry_policy, RetryPolicy) else RetryPolicy.fromDict(retry_policy),
            executionContext=dict(data.get("executionContext") or {}),
            metadata=dict(data.get("metadata") or {}),
            attempts=int(data.get("attempts") or 0),
            nextRunAt=str(data.get("nextRunAt") or ""),
            lastError=str(data.get("lastError") or ""),
            result=data.get("result"),
            recurringTask=recurring_task if isinstance(recurring_task, RecurringTask) else None,
            cancelRequested=bool(data.get("cancelRequested") or False),
            runCount=int(data.get("runCount") or 0),
        )
