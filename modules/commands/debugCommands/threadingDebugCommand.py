"""Threading debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import parse_key_value_args


class ThreadingDebugCommand(BaseCommand):
    """Inspect threading, scheduler, and task execution state."""

    path = ("debug", "threading")
    description = "Show threading and scheduler state, or end one active task. Usage: /debug threading [end name=task_name]"

    def execute(self, args):
        """Return thread/task/schedule state or request a task stop."""

        tokens = list(args or [])
        if tokens and str(tokens[0]).lower() == "end":
            return self._endTask(tokens[1:])
        return self._showState()

    def _showState(self):
        """Build a compact threading and scheduling debug snapshot."""

        threader = getattr(self.context, "threader", None)
        task_manager = getattr(self.context, "taskManager", None)
        scheduler = getattr(self.context, "scheduler", None)

        lines = []

        if threader is None:
            lines.append("threads: unavailable")
        else:
            thread_names = threader.listThreads()
            lines.append(f"threads_registered: {len(thread_names)}")
            for name in thread_names:
                thread = threader.getThread(name)
                control = threader.controls.get(name)
                is_alive = thread.is_alive() if thread else False
                is_paused = bool(control and not control.pause_event.is_set())
                stop_requested = bool(control and control.stop_event.is_set())
                lines.append(
                    f"- thread {name}: alive={is_alive}, paused={is_paused}, stop_requested={stop_requested}"
                )

        if task_manager is None:
            lines.append("tasks: unavailable")
        else:
            task_names = task_manager.listTasks()
            lines.append(f"tasks_registered: {len(task_names)}")
            for name in task_names:
                task = task_manager.getTask(name)
                if task is None:
                    continue
                lines.append(
                    f"- task {name}: completed={task.completed}, has_error={task.error is not None}"
                )

        if scheduler is None:
            lines.append("scheduler: unavailable")
        else:
            lines.append(f"scheduler_running: {scheduler.running}")
            schedule_names = scheduler.listSchedules()
            lines.append(f"schedules_registered: {len(schedule_names)}")
            for name in schedule_names:
                schedule = scheduler.getSchedule(name)
                last_ran = getattr(schedule, "last_ran", None)
                lines.append(f"- schedule {name}: last_ran={last_ran}")

        return self.ok("\n".join(lines))

    def _endTask(self, args):
        """Request a managed task thread to stop and mark intent in output."""

        fields = parse_key_value_args(args)
        task_name = fields.get("name") or fields.get("task")
        if not task_name:
            return self.fail("Usage: /debug threading end name=task_name")

        threader = getattr(self.context, "threader", None)
        task_manager = getattr(self.context, "taskManager", None)
        if threader is None or task_manager is None:
            return self.fail("Threading system unavailable.")

        task = task_manager.getTask(task_name)
        if task is None:
            return self.fail(f"Unknown task: {task_name}")

        thread_name = f"task_{task_name}"
        thread = threader.getThread(thread_name)
        if thread is None:
            return self.fail(f"Managed thread not found for task: {task_name}")

        if task.completed:
            return self.ok(f"Task already completed: {task_name}")

        threader.stopThread(thread_name)
        return self.ok(f"Stop requested for task {task_name} via thread {thread_name}.")
