"""Task lifecycle state coordination."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from threading import RLock

from .models.taskState import TaskState


class TaskStateManager:
    """Track active task lifecycle transitions."""

    def __init__(self, context=None):
        self.context = context
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Tasks.State") if getattr(context, "logger", None) else None
        self._lock = RLock()
        self._states: dict[str, str] = {}
        self._history = defaultdict(list)

    def setState(self, task, state: str):
        taskId = self._taskId(task)
        with self._lock:
            self._states[taskId] = state
            self._history[taskId].append({"state": state, "timestamp": datetime.utcnow().isoformat(timespec="seconds")})
        if hasattr(task, "state"):
            task.state = state
        return task

    def markScheduled(self, task):
        return self.setState(task, TaskState.SCHEDULED)

    def markWaiting(self, task):
        return self.setState(task, TaskState.WAITING)

    def markRunning(self, task):
        return self.setState(task, TaskState.RUNNING)

    def markCompleted(self, task):
        return self.setState(task, TaskState.COMPLETED)

    def markFailed(self, task):
        return self.setState(task, TaskState.FAILED)

    def markCancelled(self, task):
        return self.setState(task, TaskState.CANCELLED)

    def markRetrying(self, task):
        return self.setState(task, TaskState.RETRYING)

    def snapshot(self):
        with self._lock:
            return {"states": dict(self._states), "history": {key: list(value) for key, value in self._history.items()}}

    @staticmethod
    def _taskId(task):
        if isinstance(task, str):
            return task
        return str(getattr(task, "taskId", "") or getattr(task, "name", "") or "")
