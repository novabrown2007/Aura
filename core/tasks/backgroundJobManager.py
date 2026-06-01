"""Recurring background job registration."""

from __future__ import annotations

from .models.recurringTask import RecurringTask
from .models.taskPriority import TaskPriority
from .models.retryPolicy import RetryPolicy


class BackgroundJobManager:
    """Create recurring background jobs using the shared task system."""

    def __init__(self, context=None, taskManager=None):
        self.context = context
        self.taskManager = taskManager
        self.jobs: dict[str, RecurringTask] = {}

    def registerJob(self, name: str, intervalSeconds: float, target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None):
        job = RecurringTask(
            taskName=str(name),
            intervalSeconds=float(intervalSeconds),
            metadata=dict(metadata or {}),
        )
        self.jobs[job.recurringTaskId] = job
        if self.taskManager is not None:
            self.taskManager.scheduleRecurring(
                taskName=name,
                intervalSeconds=intervalSeconds,
                target=target,
                executionContext=executionContext,
                priority=priority,
                retryPolicy=retryPolicy,
                metadata=metadata,
                recurringTask=job,
            )
        return job

    def listJobs(self):
        return list(self.jobs.values())
