"""Unified lightweight async task orchestration for Aura."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from .backgroundJobManager import BackgroundJobManager
from .models.auraTask import AuraTask
from .models.retryPolicy import RetryPolicy
from .models.taskPriority import TaskPriority
from .models.taskResult import TaskResult
from .models.taskState import TaskState
from .taskCancellationManager import TaskCancellationManager
from .taskExecutor import TaskExecutor
from .taskEventHandler import TaskEventHandler
from .taskPersistenceManager import TaskPersistenceManager
from .taskQueue import TaskQueue
from .taskRegistry import TaskRegistry
from .taskRetryManager import TaskRetryManager
from .taskScheduler import TaskScheduler
from .taskStateManager import TaskStateManager
from .taskWorker import TaskWorker
from .recurringTaskManager import RecurringTaskManager
from .workers.asyncWorker import AsyncWorker
from .workers.backgroundWorker import BackgroundWorker
from .handlers.taskEventHandler import TaskEventHandler


class TaskManager:
    """Central async orchestration coordinator."""

    def __init__(self, context=None):
        self.context = context
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Tasks") if getattr(context, "logger", None) else None
        self.enabled = bool(self._configBool("taskSystemEnabled", True))
        self.defaultRetryAttempts = int(self._configValue("defaultRetryAttempts", 3) or 3)
        self.defaultRetryDelaySeconds = float(self._configValue("defaultRetryDelaySeconds", 30) or 30)
        self.running = False
        self._lock = threading.RLock()
        self._legacyTasks: dict[str, object] = {}
        self._completedHistory: list[object] = []
        self._loadedPersistedTasks = False
        self.tasks = self._legacyTasks
        self.completedTaskHistory = self._completedHistory

        self.registry = TaskRegistry(context)
        self.queue = TaskQueue()
        self.stateManager = TaskStateManager(context)
        self.persistenceManager = TaskPersistenceManager(context)
        self.retryManager = TaskRetryManager(context)
        self.cancellationManager = TaskCancellationManager(context, self.queue, self.persistenceManager)
        self.executor = TaskExecutor(context)
        maxConcurrent = int(self._configValue("maxConcurrentTasks", 5) or 5)
        self.worker = TaskWorker(context, self, maxConcurrentTasks=maxConcurrent)
        self.asyncWorker = AsyncWorker(context, self, maxConcurrentTasks=maxConcurrent)
        self.backgroundWorker = BackgroundWorker(context, self, maxConcurrentTasks=maxConcurrent)
        self.scheduler = TaskScheduler(context, self.queue, self.worker, self.stateManager, self.persistenceManager, self.retryManager, self.cancellationManager)
        self.recurringTaskManager = RecurringTaskManager(context, self)
        self.backgroundJobManager = BackgroundJobManager(context, self)
        self.eventHandler = TaskEventHandler(context, self)

        self._bindContext()
        self.eventHandler.subscribe()
        self.loadPersistedTasks()

    def _bindContext(self):
        if self.context is None:
            return
        self.context.taskManager = self
        self.context.taskQueue = self.queue
        self.context.taskRegistry = self.registry
        self.context.taskScheduler = self.scheduler
        self.context.taskPersistenceManager = self.persistenceManager
        self.context.taskRetryManager = self.retryManager
        self.context.taskCancellationManager = self.cancellationManager
        self.context.taskStateManager = self.stateManager
        self.context.taskExecutor = self.executor
        self.context.backgroundJobManager = self.backgroundJobManager
        self.context.recurringTaskManager = self.recurringTaskManager

    def start(self):
        if not self.enabled:
            return self
        if self.running:
            return self
        self.running = True
        if not self._loadedPersistedTasks:
            self.loadPersistedTasks()
        self.scheduler.start()
        return self

    def stop(self):
        if not self.enabled:
            return self
        self.running = False
        self.scheduler.stop()
        return self

    def shutdown(self):
        self.stop()
        try:
            self.eventHandler.unsubscribe()
        except Exception:
            pass
        try:
            self.persistenceManager.close()
        except Exception:
            pass

    def registerTaskDefinition(self, definition):
        return self.registry.registerTaskDefinition(definition)

    def registerRecurringTask(self, recurringTask):
        return self.registry.registerRecurringTask(recurringTask)

    def submitTask(self, task):
        legacyName = getattr(task, "name", None) or getattr(task, "taskName", None) or "task"
        with self._lock:
            existing = self._legacyTasks.get(legacyName)
            if existing is not None and not bool(getattr(existing, "completed", False)):
                raise RuntimeError(f"Task '{legacyName}' already exists.")
            if existing is not None and bool(getattr(existing, "completed", False)):
                self._completedHistory.append(existing)
            self._legacyTasks[legacyName] = task

        threader = getattr(self.context, "threader", None)
        if threader is not None:
            thread = threader.createThread(name=f"task_{legacyName}", target=self._runLegacyTask, args=(task,), daemon=True)
            thread.start()
        else:
            thread = threading.Thread(name=f"task_{legacyName}", target=self._runLegacyTask, args=(task,), daemon=True)
            thread.start()
        return task

    def scheduleTask(self, task: AuraTask):
        if not isinstance(task, AuraTask):
            task = AuraTask.fromDict(task)
        if not task.scheduledAt:
            task.scheduledAt = task.createdAt
        if not task.nextRunAt:
            task.nextRunAt = task.scheduledAt
        self.stateManager.markScheduled(task)
        self.persistenceManager.persistTask(task)
        self.queue.enqueue(task)
        self._emit("task.created", {"task": task.asDict()})
        self._emit("task.scheduled", {"task": task.asDict()})
        return task

    def scheduleDelayed(self, taskName: str, delaySeconds: float, taskType: str = "callable", target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None):
        runAt = datetime.utcnow() + timedelta(seconds=float(delaySeconds))
        task = AuraTask(
            taskName=str(taskName),
            taskType=str(taskType),
            scheduledAt=runAt.isoformat(timespec="seconds"),
            nextRunAt=runAt.isoformat(timespec="seconds"),
            priority=str(priority or TaskPriority.NORMAL),
            executionContext=dict(executionContext or {}),
            metadata=dict(metadata or {}),
            retryPolicy=self._normalizeRetryPolicy(retryPolicy),
        )
        if target is not None:
            task.executionContext.setdefault("target", target)
        return self.scheduleTask(task)

    def scheduleAt(self, runAt: datetime, taskName: str, taskType: str = "callable", target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None):
        task = AuraTask(
            taskName=str(taskName),
            taskType=str(taskType),
            scheduledAt=runAt.isoformat(timespec="seconds"),
            nextRunAt=runAt.isoformat(timespec="seconds"),
            priority=str(priority or TaskPriority.NORMAL),
            executionContext=dict(executionContext or {}),
            metadata=dict(metadata or {}),
            retryPolicy=self._normalizeRetryPolicy(retryPolicy),
        )
        if target is not None:
            task.executionContext.setdefault("target", target)
        return self.scheduleTask(task)

    def scheduleRecurring(self, taskName: str, intervalSeconds: float, taskType: str = "callable", target=None, executionContext: dict | None = None, priority: str = TaskPriority.NORMAL, retryPolicy: RetryPolicy | dict | None = None, metadata: dict | None = None, recurringTask=None):
        recurringTask = recurringTask or self.recurringTaskManager.createRecurringTask(taskName, intervalSeconds, metadata=metadata)
        recurringTask.nextRunAt = recurringTask.computeNextRun()
        executionContext = dict(executionContext or {})
        executionContext.setdefault("recurringTask", recurringTask.asDict())
        task = AuraTask(
            taskName=str(taskName),
            taskType=str(taskType),
            scheduledAt=recurringTask.nextRunAt,
            nextRunAt=recurringTask.nextRunAt,
            priority=str(priority or TaskPriority.NORMAL),
            executionContext=executionContext,
            metadata=dict(metadata or {}),
            retryPolicy=self._normalizeRetryPolicy(retryPolicy),
            recurringTask=recurringTask,
        )
        if target is not None:
            task.executionContext.setdefault("target", target)
        self.registerRecurringTask(recurringTask)
        return self.scheduleTask(task)

    def cancelTask(self, task):
        if task is None:
            return None
        if not isinstance(task, AuraTask):
            taskId = str(getattr(task, "taskId", "") or getattr(task, "name", "") or task)
            task = self.queue.get(taskId) or self.persistenceManager.loadTask(taskId) or task
            if isinstance(task, dict):
                task = AuraTask.fromDict(task)
        self.cancellationManager.cancelTask(task)
        self._emit("task.cancelled", {"task": task.asDict() if hasattr(task, "asDict") else task})
        return task

    def tick(self):
        return self.scheduler.tick()

    def loadPersistedTasks(self):
        tasks = self.persistenceManager.loadPendingTasks()
        for task in tasks:
            self.queue.enqueue(task)
        self._loadedPersistedTasks = True
        return tasks

    def getTask(self, name: str):
        with self._lock:
            legacy = self._legacyTasks.get(name)
        if legacy is not None:
            return legacy
        return self.queue.get(name) or self.persistenceManager.loadTask(name)

    def listTasks(self):
        with self._lock:
            active = list(self._legacyTasks.keys())
        active.extend(getattr(task, "taskId", "") for task in self.queue.listTasks())
        return [item for item in active if item]

    def completedTasks(self):
        with self._lock:
            completed = list(self._completedHistory)
        return completed

    def snapshot(self):
        return {
            "available": True,
            "enabled": self.enabled,
            "running": self.running,
            "scheduled": [task.asDict() for task in self.queue.listTasks()],
            "registry": [definition.asDict() for definition in self.registry.listTaskDefinitions()],
            "recurring": [task.asDict() for task in self.registry.listRecurringTasks()],
            "state": self.stateManager.snapshot(),
        }

    def _runLegacyTask(self, task, threadControl=None):
        name = getattr(task, "name", None) or getattr(task, "taskName", None) or "task"
        try:
            self._emit("task.started", {"task": task})
            if hasattr(task, "run"):
                task.run()
                if getattr(task, "error", None) is not None:
                    self._emit("task.failed", {"task": task, "error": str(task.error)})
                else:
                    self._emit("task.completed", {"task": task, "result": getattr(task, "result", None)})
        finally:
            with self._lock:
                self._legacyTasks.pop(name, None)
                self._completedHistory.append(task)
        return getattr(task, "result", None)

    def _runQueuedTask(self, task):
        if task.cancelRequested:
            self.stateManager.markCancelled(task)
            self._emit("task.cancelled", {"task": task.asDict()})
            return None

        self.stateManager.markRunning(task)
        self._emit("task.started", {"task": task.asDict()})
        result = self.executor.executeTask(task)
        task.runCount = int(getattr(task, "runCount", 0) or 0) + 1
        self.persistenceManager.persistTask(task)
        if result.status == TaskState.COMPLETED:
            self.stateManager.markCompleted(task)
            self._emit("task.completed", {"task": task.asDict(), "result": result.asDict()})
            if getattr(task, "recurringTask", None) is not None:
                self._rescheduleRecurring(task)
        else:
            self.stateManager.markFailed(task)
            self._emit("task.failed", {"task": task.asDict(), "result": result.asDict()})
            if self.retryManager.shouldRetry(task, result.errors):
                retryTask = self.retryManager.scheduleRetry(task, result.errors)
                self.persistenceManager.persistTask(retryTask)
                self.queue.enqueue(retryTask)
                self._emit("task.retrying", {"task": retryTask.asDict(), "errors": list(result.errors or [])})
        return result

    def _rescheduleRecurring(self, task):
        self.recurringTaskManager.reschedule(task)
        self.persistenceManager.persistTask(task)
        self.queue.enqueue(task)
        self._emit("task.scheduled", {"task": task.asDict(), "recurring": True})

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        return eventManager.emit(eventName, data)

    def _configBool(self, key: str, default: bool = False) -> bool:
        return bool(self._configValue(key, default))

    def _configValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    def _normalizeRetryPolicy(self, retryPolicy):
        if isinstance(retryPolicy, RetryPolicy):
            return retryPolicy
        data = dict(retryPolicy or {})
        if not data:
            data = {
                "maxRetries": self.defaultRetryAttempts,
                "retryDelaySeconds": self.defaultRetryDelaySeconds,
                "backoffMultiplier": 2.0,
                "retryOnFailure": True,
            }
        return RetryPolicy.fromDict(data)
