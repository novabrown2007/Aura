"""Task-related calendar commands for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import format_result, parse_key_value_args


class TaskCreateCommand(BaseCommand):
    """Create a calendar task."""

    path = ("calendar", "task", "create")
    description = "Create a task. Usage: /calendar task create title='Pay rent' [due_at='12:00 24/03/2026']"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "title" not in fields:
            return self.fail("Usage: /calendar task create title='Pay rent' [due_at='12:00 24/03/2026']")
        task_id = self.context.require("calendar").createTask(**fields)
        return self.ok(f"Created task {task_id}: {fields['title']}")


class TaskGetCommand(BaseCommand):
    """Get one task by ID."""

    path = ("calendar", "task", "get")
    description = "Get one task. Usage: /calendar task get id=1"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar task get id=1")
        return self.ok(format_result(self.context.require("calendar").getTask(int(fields["id"]))))


class TaskListCommand(BaseCommand):
    """List or search tasks."""

    path = ("calendar", "task", "list")
    description = "List tasks. Usage: /calendar task list [calendar_id=1] [status=pending] [priority=high]"

    def execute(self, args):
        fields = parse_key_value_args(args)
        calendar = self.context.require("calendar")
        if any(key in fields for key in ("query", "priority", "due_before", "due_after")):
            rows = calendar.searchTasks(
                query=fields.get("query"),
                calendar_id=fields.get("calendar_id"),
                status=fields.get("status"),
                priority=fields.get("priority"),
                due_before=fields.get("due_before"),
                due_after=fields.get("due_after"),
            )
        else:
            rows = calendar.listTasks(
                calendar_id=fields.get("calendar_id"),
                status=fields.get("status"),
            )
        return self.ok(format_result(rows))


class TaskUpdateCommand(BaseCommand):
    """Update one task."""

    path = ("calendar", "task", "update")
    description = "Update a task. Usage: /calendar task update id=1 status=completed"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar task update id=1 status=completed")
        task_id = int(fields.pop("id"))
        self.context.require("calendar").updateTask(task_id, **fields)
        return self.ok(f"Updated task {task_id}.")


class TaskDeleteCommand(BaseCommand):
    """Delete one task."""

    path = ("calendar", "task", "delete")
    description = "Delete a task. Usage: /calendar task delete id=1"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar task delete id=1")
        task_id = int(fields["id"])
        self.context.require("calendar").deleteTask(task_id)
        return self.ok(f"Deleted task {task_id}.")


def build_commands(context):
    """Return task command objects for registry registration."""

    return [
        TaskCreateCommand(context),
        TaskGetCommand(context),
        TaskListCommand(context),
        TaskUpdateCommand(context),
        TaskDeleteCommand(context),
    ]
