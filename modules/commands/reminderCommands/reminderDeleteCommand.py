"""Reminder deletion command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.reminderCommands._reminderCommandUtils import parse_key_value_args


class ReminderDeleteCommand(BaseCommand):
    """Delete one shared reminder by ID."""

    path = ("reminder", "delete")
    description = "Delete one reminder. Usage: /reminder delete id=1"

    def execute(self, args):
        """Delete one reminder row."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /reminder delete id=1")

        reminder_id = int(fields["id"])
        self.context.require("reminders").deleteReminder(reminder_id)
        return self.ok(f"Deleted reminder {reminder_id}.")
