"""Command-system implementation for `tasksCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class TasksCommand(BaseCommand):
    """
    Lists and cancels background tasks.
    """

    name = "tasks"
    help_message = "List or cancel tasks."

    def __init__(self, context):
        """Initialize `TasksCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.systemCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        manager = self.context.require("taskManager")

        if not args:
            return self._usage()

        action = args[0].lower()

        if action == "list":
            tasks = manager.tasks
            if not tasks:
                return "No tasks are currently registered."

            lines = ["------ TASKS ------"]
            for task_name, task in tasks.items():
                status = "completed" if task.completed else "running"
                if task.error:
                    status = f"error: {task.error}"
                lines.append(f"{task_name} [{status}]")
            return "\n".join(lines)

        if action == "cancel":
            if len(args) < 2:
                return "Usage: /system tasks cancel <id>"

            task_name = args[1]
            task = manager.getTask(task_name)
            if not task:
                return f'Task "{task_name}" not found.'

            thread_name = f"task_{task_name}"
            try:
                self.context.require("threader").stopThread(thread_name)
                return f'Task "{task_name}" cancel requested.'
            except Exception as error:
                return f'Unable to cancel task "{task_name}": {error}'

        return self._usage()

    @staticmethod
    def _usage() -> str:
        """Implement `_usage` as part of this component's public/internal behavior."""
        return "Usage:\n/system tasks list\n/system tasks cancel <id>"

