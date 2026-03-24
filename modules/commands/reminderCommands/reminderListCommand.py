"""Reminder list command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.reminderCommands._reminderCommandUtils import format_result


class ReminderListCommand(BaseCommand):
    """List all shared reminders."""

    path = ("reminder", "list")
    description = "List all reminders."

    def execute(self, args):
        """Return all reminder rows."""

        rows = self.context.require("reminders").listReminders()
        return self.ok(format_result(rows))
