"""Registry for reusable task definitions and recurring jobs."""

from __future__ import annotations

from threading import RLock

from .models.taskDefinition import TaskDefinition
from .models.recurringTask import RecurringTask


class TaskRegistry:
    """Keep task definitions discoverable and reusable."""

    def __init__(self, context=None):
        self.context = context
        self._lock = RLock()
        self._definitions: dict[str, TaskDefinition] = {}
        self._recurring: dict[str, RecurringTask] = {}

    def registerTaskDefinition(self, definition: TaskDefinition):
        with self._lock:
            self._definitions[str(definition.taskName)] = definition
        return definition

    def getTaskDefinition(self, name: str):
        with self._lock:
            return self._definitions.get(str(name))

    def listTaskDefinitions(self):
        with self._lock:
            return list(self._definitions.values())

    def registerRecurringTask(self, recurringTask: RecurringTask):
        with self._lock:
            self._recurring[str(recurringTask.recurringTaskId)] = recurringTask
        return recurringTask

    def getRecurringTask(self, recurringTaskId: str):
        with self._lock:
            return self._recurring.get(str(recurringTaskId))

    def listRecurringTasks(self):
        with self._lock:
            return list(self._recurring.values())
