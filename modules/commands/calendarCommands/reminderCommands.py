"""Reminder-related calendar commands for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import format_result, parse_key_value_args


class ReminderCreateCommand(BaseCommand):
    """Create a calendar reminder."""

    path = ("calendar", "reminder", "create")
    description = "Create a calendar reminder. Usage: /calendar reminder create title='Leave now' remind_at='12:30 24/03/2026'"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "title" not in fields or "remind_at" not in fields:
            return self.fail("Usage: /calendar reminder create title='Leave now' remind_at='12:30 24/03/2026'")
        reminder_id = self.context.require("calendar").createReminder(**fields)
        return self.ok(f"Created calendar reminder {reminder_id}: {fields['title']}")


class ReminderGetCommand(BaseCommand):
    """Get one calendar reminder by ID."""

    path = ("calendar", "reminder", "get")
    description = "Get one calendar reminder. Usage: /calendar reminder get id=1"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar reminder get id=1")
        return self.ok(format_result(self.context.require("calendar").getReminder(int(fields["id"]))))


class ReminderListCommand(BaseCommand):
    """List or search calendar reminders."""

    path = ("calendar", "reminder", "list")
    description = "List calendar reminders. Usage: /calendar reminder list [calendar_id=1] [event_id=1] [include_delivered=false]"

    def execute(self, args):
        fields = parse_key_value_args(args)
        calendar = self.context.require("calendar")
        if any(key in fields for key in ("query", "event_id", "task_id", "remind_before", "remind_after")):
            rows = calendar.searchReminders(
                query=fields.get("query"),
                calendar_id=fields.get("calendar_id"),
                event_id=fields.get("event_id"),
                task_id=fields.get("task_id"),
                include_delivered=fields.get("include_delivered", True),
                remind_before=fields.get("remind_before"),
                remind_after=fields.get("remind_after"),
            )
        else:
            rows = calendar.listReminders(
                calendar_id=fields.get("calendar_id"),
                include_delivered=fields.get("include_delivered", True),
            )
        return self.ok(format_result(rows))


class ReminderUpdateCommand(BaseCommand):
    """Update one calendar reminder."""

    path = ("calendar", "reminder", "update")
    description = "Update a calendar reminder. Usage: /calendar reminder update id=1 title='New title'"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar reminder update id=1 title='New title'")
        reminder_id = int(fields.pop("id"))
        self.context.require("calendar").updateReminder(reminder_id, **fields)
        return self.ok(f"Updated calendar reminder {reminder_id}.")


class ReminderDeleteCommand(BaseCommand):
    """Delete one calendar reminder."""

    path = ("calendar", "reminder", "delete")
    description = "Delete a calendar reminder. Usage: /calendar reminder delete id=1"

    def execute(self, args):
        fields = parse_key_value_args(args)
        if "id" not in fields:
            return self.fail("Usage: /calendar reminder delete id=1")
        reminder_id = int(fields["id"])
        self.context.require("calendar").deleteReminder(reminder_id)
        return self.ok(f"Deleted calendar reminder {reminder_id}.")


class ReminderProcessDueCommand(BaseCommand):
    """Trigger due calendar reminder processing."""

    path = ("calendar", "reminder", "processdue")
    description = "Process due calendar reminders immediately."

    def execute(self, args):
        rows = self.context.require("calendar").processDueReminders()
        return self.ok(format_result(rows))


def build_commands(context):
    """Return reminder command objects for registry registration."""

    return [
        ReminderCreateCommand(context),
        ReminderGetCommand(context),
        ReminderListCommand(context),
        ReminderUpdateCommand(context),
        ReminderDeleteCommand(context),
        ReminderProcessDueCommand(context),
    ]
