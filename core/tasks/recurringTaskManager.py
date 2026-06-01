"""Recurring task coordination."""

from __future__ import annotations

from datetime import datetime

from .models.recurringTask import RecurringTask


class RecurringTaskManager:
    """Manage recurring task definitions and rescheduling."""

    def __init__(self, context=None, taskManager=None):
        self.context = context
        self.taskManager = taskManager
        self.recurringTasks: dict[str, RecurringTask] = {}

    def register(self, recurringTask: RecurringTask):
        self.recurringTasks[recurringTask.recurringTaskId] = recurringTask
        return recurringTask

    def createRecurringTask(self, taskName: str, intervalSeconds: float, metadata: dict | None = None):
        recurringTask = RecurringTask(
            taskName=str(taskName),
            intervalSeconds=float(intervalSeconds),
            metadata=dict(metadata or {}),
        )
        return self.register(recurringTask)

    def reschedule(self, task):
        recurringTask = getattr(task, "recurringTask", None)
        if recurringTask is None and hasattr(task, "executionContext"):
            recurringTask = (task.executionContext or {}).get("recurringTask")
        if recurringTask is None:
            return None
        if not isinstance(recurringTask, RecurringTask):
            recurringTask = RecurringTask.fromDict(recurringTask) if hasattr(RecurringTask, "fromDict") else RecurringTask()
        task.recurringTask = recurringTask
        nextRun = recurringTask.computeNextRun(datetime.utcnow())
        recurringTask.nextRunAt = nextRun
        task.scheduledAt = nextRun
        task.nextRunAt = nextRun
        task.state = "SCHEDULED"
        return task
