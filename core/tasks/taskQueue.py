"""Thread-safe priority queue for due tasks."""

from __future__ import annotations

import heapq
import threading
from dataclasses import dataclass, field

from .models.taskPriority import TaskPriority
from .utilities.taskTimeUtils import TaskTimeUtils


@dataclass(order=True)
class _QueueItem:
    sortKey: tuple = field(init=False)
    runAt: str = ""
    priorityWeight: int = 0
    sequence: int = 0
    taskId: str = ""
    task: object = None

    def __post_init__(self):
        self.sortKey = (
            self.runAt or "",
            self.priorityWeight,
            self.sequence,
        )


class TaskQueue:
    """Maintain due tasks in deterministic order."""

    def __init__(self):
        self._lock = threading.RLock()
        self._items: list[_QueueItem] = []
        self._index: dict[str, _QueueItem] = {}
        self._sequence = 0

    def enqueue(self, task):
        with self._lock:
            self._sequence += 1
            scheduled = getattr(task, "scheduledAt", "") or getattr(task, "nextRunAt", "") or TaskTimeUtils.toIso()
            priority = TaskPriority.weight(getattr(task, "priority", TaskPriority.NORMAL))
            item = _QueueItem(runAt=str(scheduled), priorityWeight=priority, sequence=self._sequence, taskId=str(getattr(task, "taskId", "")), task=task)
            heapq.heappush(self._items, item)
            self._index[item.taskId] = item

    def popDue(self, now=None):
        with self._lock:
            due = []
            while self._items:
                item = self._items[0]
                if item.taskId not in self._index:
                    heapq.heappop(self._items)
                    continue
                if not TaskTimeUtils.isDue(item.runAt, now=now):
                    break
                heapq.heappop(self._items)
                self._index.pop(item.taskId, None)
                due.append(item.task)
            return due

    def remove(self, taskId: str):
        with self._lock:
            self._index.pop(str(taskId), None)

    def listTasks(self):
        with self._lock:
            return [item.task for item in self._items if item.taskId in self._index]

    def get(self, taskId: str):
        with self._lock:
            item = self._index.get(str(taskId))
            return item.task if item is not None else None

    def clear(self):
        with self._lock:
            self._items.clear()
            self._index.clear()
