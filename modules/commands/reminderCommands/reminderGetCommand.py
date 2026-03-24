"""Reminder lookup command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.reminderCommands._reminderCommandUtils import format_result, parse_key_value_args


class ReminderGetCommand(BaseCommand):
    """Fetch one shared reminder by ID."""

    path = ("reminder", "get")
    description = "Get one reminder. Usage: /reminder get id=1"

    def execute(self, args):
        """Return one reminder row."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /reminder get id=1")

        reminder = self.context.require("reminders").getReminder(int(fields["id"]))
        return self.ok(format_result(reminder))
