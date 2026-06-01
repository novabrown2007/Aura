"""Cancellation support for scheduled tasks."""

from __future__ import annotations

from .models.taskState import TaskState


class TaskCancellationManager:
    """Cancel queued or persisted tasks safely."""

    def __init__(self, context=None, queue=None, persistenceManager=None):
        self.context = context
        self.queue = queue
        self.persistenceManager = persistenceManager

    def cancelTask(self, task, reason: str = "cancelled"):
        if task is None:
            return None
        task.cancelRequested = True
        task.state = TaskState.CANCELLED
        task.lastError = str(reason or "cancelled")
        if self.queue is not None:
            self.queue.remove(getattr(task, "taskId", ""))
        if self.persistenceManager is not None:
            self.persistenceManager.persistTask(task)
        self._emit("task.cancelled", {"task": task.asDict() if hasattr(task, "asDict") else task, "reason": reason})
        return task

    def _emit(self, eventName: str, data: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return None
        return eventManager.emit(eventName, data)
