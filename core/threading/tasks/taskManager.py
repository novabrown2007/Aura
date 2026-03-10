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
            self.logger = context.logger.getChild("Tasks")

        self.tasks: Dict[str, Task] = {}
        """Dictionary of tasks indexed by task name."""

        if self.logger:
            self.logger.info(f"taskManager.py has been initialized.")

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

        if task.name in self.tasks:
            raise RuntimeError(f"Task '{task.name}' already exists.")

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

        task.run()

        if task.error:
            if self.logger:
                self.logger.error(f"Task failed: {task.name} ({task.error})")
        else:
            if self.logger:
                self.logger.debug(f"Task completed: {task.name}")

        # Emit completion event if event system exists
        if self.context.eventManager:
            from core.threading.events.events import Event

            self.context.eventManager.emit(
                Event("task_completed", {"task": task})
            )

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

        return self.tasks.get(name)

    def listTasks(self):
        """
        List all registered tasks.

        Returns:
            list[str]
        """

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

        return [task for task in self.tasks.values() if task.completed]
