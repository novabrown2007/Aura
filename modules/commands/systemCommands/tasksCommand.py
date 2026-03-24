"""System tasks command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class TasksCommand(BaseCommand):
    """List registered background tasks."""

    path = ("system", "tasks")
    description = "List registered background tasks."

    def execute(self, args):
        """Return known task names."""

        task_names = self.context.require("taskManager").listTasks()
        return self.ok("Tasks:\n" + ("\n".join(task_names) if task_names else "none"))

