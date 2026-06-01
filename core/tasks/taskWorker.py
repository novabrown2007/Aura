"""Worker utilities for executing queued tasks."""

from __future__ import annotations

import threading


class TaskWorker:
    """Dispatch tasks with a concurrency gate."""

    def __init__(self, context=None, taskManager=None, maxConcurrentTasks: int = 5):
        self.context = context
        self.taskManager = taskManager
        self.maxConcurrentTasks = int(maxConcurrentTasks or 1)
        self._semaphore = threading.Semaphore(self.maxConcurrentTasks)

    def dispatch(self, task):
        if not self._semaphore.acquire(blocking=False):
            return False

        taskId = str(getattr(task, "taskId", "") or getattr(task, "taskName", "") or "task")

        threader = getattr(self.context, "threader", None)
        if threader is not None:
            thread = threader.createThread(
                name=f"task_{taskId}",
                target=self._execute,
                args=(task,),
                daemon=True,
            )
            thread.start()
            return thread

        thread = threading.Thread(
            name=f"task_{taskId}",
            target=self._execute,
            args=(task,),
            daemon=True,
        )
        thread.start()
        return thread

    def _execute(self, task, threadControl=None):
        try:
            if self.taskManager is not None:
                self.taskManager._runQueuedTask(task)
        finally:
            self._semaphore.release()
