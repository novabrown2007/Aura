"""Unified lightweight scheduler for Aura tasks."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models.auraTask import AuraTask
from .models.taskPriority import TaskPriority
from .models.taskState import TaskState
from .models.retryPolicy import RetryPolicy
from .scheduling.schedulerLoop import SchedulerLoop
from .scheduling.delayedExecutionScheduler import DelayedExecutionScheduler
from .scheduling.recurringScheduler import RecurringScheduler


class TaskScheduler:
    """Coordinate delayed, recurring, and queued execution."""

    def __init__(self, context=None, taskQueue=None, worker=None, stateManager=None, persistenceManager=None, retryManager=None, cancellationManager=None):
        self.context = context
        self.taskQueue = taskQueue
        self.worker = worker
        self.stateManager = stateManager
        self.persistenceManager = persistenceManager
        self.retryManager = retryManager
        self.cancellationManager = cancellationManager
        self.loop = SchedulerLoop(self, float(self._config("taskSchedulerTickIntervalMs", 500)) / 1000.0)
        self.delayedScheduler = DelayedExecutionScheduler(self)
        self.recurringScheduler = RecurringScheduler(self)

    def start(self):
        if self.loop.running:
            return None
        self.loop.start()
        threader = getattr(self.context, "threader", None)
        if threader is not None:
            thread = threader.createThread(name="task_scheduler_loop", target=self.loop.run, daemon=True)
            thread.start()
            return thread
        return None

    def stop(self):
        self.loop.stop()

    def tick(self):
        due = self.taskQueue.popDue()
        for task in due:
            if getattr(task, "cancelRequested", False) or getattr(task, "state", "") == TaskState.CANCELLED:
                continue
            if self.stateManager is not None:
                self.stateManager.markWaiting(task)
            if self.worker is not None:
                dispatched = self.worker.dispatch(task)
                if not dispatched:
                    self.taskQueue.enqueue(task)
        return due

    def scheduleTask(self, task: AuraTask):
        if task.scheduledAt == "":
            task.scheduledAt = task.createdAt
        task.state = TaskState.SCHEDULED
        if self.stateManager is not None:
            self.stateManager.markScheduled(task)
        if self.persistenceManager is not None:
            self.persistenceManager.persistTask(task)
        self.taskQueue.enqueue(task)
        self._emit("task.scheduled", {"task": task.asDict()})
        return task

    def scheduleDelayed(self, delaySeconds: float, taskName: str, taskType: str = "callable", target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None, recurringTask=None):
        scheduledAt = datetime.utcnow()
        runAt = (scheduledAt + timedelta(seconds=float(delaySeconds))).isoformat(timespec="seconds")
        task = AuraTask(
            taskName=str(taskName),
            taskType=str(taskType),
            priority=str(priority or TaskPriority.NORMAL),
            scheduledAt=runAt,
            nextRunAt=runAt,
            executionContext=dict(executionContext or {}),
            metadata=dict(metadata or {}),
            retryPolicy=retryPolicy if isinstance(retryPolicy, RetryPolicy) else RetryPolicy.fromDict(retryPolicy),
            recurringTask=recurringTask,
        )
        if target is not None:
            task.executionContext.setdefault("target", target)
        return self.scheduleTask(task)

    def scheduleAt(self, runAt, taskName: str, taskType: str = "callable", target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None, recurringTask=None):
        task = AuraTask(
            taskName=str(taskName),
            taskType=str(taskType),
            priority=str(priority or TaskPriority.NORMAL),
            scheduledAt=runAt.isoformat(timespec="seconds"),
            nextRunAt=runAt.isoformat(timespec="seconds"),
            executionContext=dict(executionContext or {}),
            metadata=dict(metadata or {}),
            retryPolicy=retryPolicy if isinstance(retryPolicy, RetryPolicy) else RetryPolicy.fromDict(retryPolicy),
            recurringTask=recurringTask,
        )
        if target is not None:
            task.executionContext.setdefault("target", target)
        return self.scheduleTask(task)

    def scheduleRecurring(self, taskName: str, intervalSeconds: float, taskType: str = "callable", target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None, recurringTask=None):
        scheduledAt = datetime.utcnow()
        recurringTask = recurringTask or __import__("core.tasks.models.recurringTask", fromlist=["RecurringTask"]).RecurringTask(
            taskName=str(taskName),
            intervalSeconds=float(intervalSeconds),
        )
        recurringTask.nextRunAt = recurringTask.computeNextRun(scheduledAt)
        task = AuraTask(
            taskName=str(taskName),
            taskType=str(taskType),
            priority=str(priority or TaskPriority.NORMAL),
            scheduledAt=recurringTask.nextRunAt,
            nextRunAt=recurringTask.nextRunAt,
            executionContext=dict(executionContext or {}),
            metadata=dict(metadata or {}),
            retryPolicy=retryPolicy if isinstance(retryPolicy, RetryPolicy) else RetryPolicy.fromDict(retryPolicy),
            recurringTask=recurringTask,
        )
        if target is not None:
            task.executionContext.setdefault("target", target)
        self.recurringScheduler.taskManager = self
        return self.scheduleTask(task)

    def cancelTask(self, task):
        if task is None:
            return None
        if self.cancellationManager is not None:
            return self.cancellationManager.cancelTask(task)
        task.state = TaskState.CANCELLED
        self.taskQueue.remove(task.taskId)
        return task

    def loadPersistedTasks(self):
        if self.persistenceManager is None:
            return []
        tasks = self.persistenceManager.loadPendingTasks()
        for task in tasks:
            self.taskQueue.enqueue(task)
        return tasks

    def _rescheduleRecurring(self, task):
        if getattr(task, "recurringTask", None) is None:
            return None
        nextRun = task.recurringTask.computeNextRun(datetime.utcnow())
        task.nextRunAt = nextRun
        task.scheduledAt = nextRun
        task.state = TaskState.SCHEDULED
        if self.persistenceManager is not None:
            self.persistenceManager.persistTask(task)
        self.taskQueue.enqueue(task)
        return task

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        return eventManager.emit(eventName, data)

    def _config(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
