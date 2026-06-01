"""Persistence bridge for Aura tasks."""

from __future__ import annotations

import os
from pathlib import Path

from .models.auraTask import AuraTask
from .models.taskState import TaskState
from .persistence.sqliteTaskStore import SQLiteTaskStore


class TaskPersistenceManager:
    """Persist and recover task definitions across restarts."""

    def __init__(self, context=None, store=None):
        self.context = context
        self.store = store or self._buildStore()

    def persistTask(self, task):
        if self.store is None or task is None:
            return None
        payload = task.asDict() if hasattr(task, "asDict") else dict(task or {})
        payload["executionContext"] = self._sanitize(payload.get("executionContext"))
        payload["metadata"] = self._sanitize(payload.get("metadata"))
        payload["result"] = self._sanitize(payload.get("result"))
        self.store.upsertTask(payload)
        return task

    def deleteTask(self, taskId: str):
        if self.store is not None:
            self.store.deleteTask(taskId)

    def loadPendingTasks(self):
        if self.store is None:
            return []
        rows = self.store.loadTasks(states=[TaskState.PENDING, TaskState.SCHEDULED, TaskState.WAITING, TaskState.RETRYING])
        return [AuraTask.fromDict(row) for row in rows]

    def loadAll(self):
        if self.store is None:
            return []
        return [AuraTask.fromDict(row) for row in self.store.loadTasks()]

    def close(self):
        if self.store is not None:
            self.store.close()

    def _sanitize(self, value):
        if isinstance(value, dict):
            sanitized = {}
            for key, item in value.items():
                if callable(item):
                    sanitized[key] = getattr(item, "__name__", "callable")
                else:
                    sanitized[key] = self._sanitize(item)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if callable(value):
            return getattr(value, "__name__", "callable")
        return value

    def _buildStore(self):
        config = getattr(self.context, "config", None)
        if config is not None and hasattr(config, "get") and not bool(config.get("taskPersistenceEnabled", True)):
            return None
        path = None
        if config is not None and hasattr(config, "get"):
            path = config.get("task.databasePath", None)
            if path is None:
                path = config.get("taskStorePath", None)
        if not path:
            path = os.path.join(".aura", "tasks.sqlite3")
        return SQLiteTaskStore(Path(path))
