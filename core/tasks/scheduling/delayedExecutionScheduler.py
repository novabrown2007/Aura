"""Delayed execution helpers."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models.taskState import TaskState


class DelayedExecutionScheduler:
    """Build delayed tasks with normalized timestamps."""

    def __init__(self, taskManager=None):
        self.taskManager = taskManager

    def executeAfter(self, seconds: float, **kwargs):
        return self.taskManager.scheduleDelayed(delaySeconds=seconds, **kwargs)

    def executeAt(self, runAt: datetime, **kwargs):
        return self.taskManager.scheduleAt(runAt, **kwargs)
