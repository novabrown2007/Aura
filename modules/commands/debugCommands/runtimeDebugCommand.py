from modules.commands.baseCommand import BaseCommand


class RuntimeDebugCommand(BaseCommand):
    """
    Debug command for runtime diagnostics.
    """

    name = "runtime"
    help_message = "Runtime diagnostics (threads, tasks, scheduler)."

    def __init__(self, context):
        super().__init__(context)
        context.debugCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        context = self.context

        thread_count = 0
        task_total = 0
        task_completed = 0
        scheduler_running = False

        if getattr(context, "threader", None):
            thread_count = len(context.threader.listThreads())

        if getattr(context, "taskManager", None):
            task_total = len(context.taskManager.tasks)
            task_completed = len(context.taskManager.completedTasks())

        if getattr(context, "scheduler", None):
            scheduler_running = bool(context.scheduler.running)

        return (
            "------ RUNTIME ------\n"
            f"threads: {thread_count}\n"
            f"tasks: {task_total}\n"
            f"tasks_completed: {task_completed}\n"
            f"scheduler_running: {scheduler_running}"
        )

