"""Core implementation for `taskManager` in the Aura assistant project."""

import threading
from typing import Dict, Optional
from .task import Task


class TaskManager:
    """
    Manages background task execution within the Aura assistant.

    The TaskManager is responsible for executing Task objects in
    separate threads using the ThreadingManager.

    It tracks running and completed tasks and provides methods
    for submitting and retrieving tasks.
    """

    def __init__(self, context):
        """
        Initialize the TaskManager.

        Args:
            context (RuntimeContext):
                Global runtime context.
        """

        self.context = context
        self.logger = None

        if context.logger:
            self.logger = context.logger.getChild("Threading.Tasks")

        self.tasks: Dict[str, Task] = {}
        """Dictionary of tasks indexed by task name."""

        self.completedTaskHistory: list[Task] = []
        """Completed tasks retained for diagnostics."""

        self._lock = threading.RLock()

        if self.logger:
            self.logger.info("Task manager initialized.")

    # --------------------------------------------------
    # Task Submission
    # --------------------------------------------------

    def submitTask(self, task: Task):
        """
        Submit a task for execution.

        The task will be executed in a separate thread.

        Args:
            task (Task):
                Task instance to execute.
        """

        with self._lock:
            existing = self.tasks.get(task.name)
            if existing is not None and not existing.completed:
                raise RuntimeError(f"Task '{task.name}' already exists.")
            if existing is not None and existing.completed:
                self.completedTaskHistory.append(existing)
            self.tasks[task.name] = task

        if self.logger:
            self.logger.debug(f"Task submitted: {task.name}")

        thread = self.context.threader.createThread(
            name=f"task_{task.name}",
            target=self._runTask,
            args=(task,),
            daemon=True
        )

        thread.start()

    # --------------------------------------------------
    # Task Execution
    # --------------------------------------------------

    def _runTask(self, task: Task, threadControl=None):
        """
        Internal wrapper used to execute tasks inside threads.

        Args:
            task (Task):
                Task to execute.

            threadControl:
                Optional thread control object injected by ThreadingManager.
        """

        if self.logger:
            self.logger.debug(f"Task started: {task.name}")

        observability = getattr(self.context, "observability", None)
        if observability is not None:
            observability.recordTrace("task", task.name, status="started")

        try:
            task.run()

            if task.error:
                if observability is not None:
                    observability.recordTrace("task", task.name, status="failed", details={"error": str(task.error)})
                if self.logger:
                    self.logger.error(f"Task failed: {task.name} ({task.error})")
            else:
                if observability is not None:
                    observability.recordTrace("task", task.name, status="completed")
                if self.logger:
                    self.logger.debug(f"Task completed: {task.name}")

            # Emit completion event if event system exists
            if self.context.eventManager:
                self.context.eventManager.emit("task_completed", {"task": task})
        finally:
            with self._lock:
                if self.tasks.get(task.name) is task:
                    self.tasks.pop(task.name, None)
                self.completedTaskHistory.append(task)

    # --------------------------------------------------
    # Task Access
    # --------------------------------------------------

    def getTask(self, name: str) -> Optional[Task]:
        """
        Retrieve a task by name.

        Args:
            name (str)

        Returns:
            Task | None
        """

        with self._lock:
            return self.tasks.get(name)

    def listTasks(self):
        """
        List all registered tasks.

        Returns:
            list[str]
        """

        with self._lock:
            return list(self.tasks.keys())

    # --------------------------------------------------
    # Debug Helpers
    # --------------------------------------------------

    def completedTasks(self):
        """
        Return all completed tasks.

        Returns:
            list[Task]
        """

        with self._lock:
            completed = list(self.completedTaskHistory)
            completed.extend(task for task in self.tasks.values() if task.completed)
            return completed
