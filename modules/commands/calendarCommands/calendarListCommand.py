"""Calendar list command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import format_result


class CalendarListCommand(BaseCommand):
    """List available calendars."""

    path = ("calendar", "list")
    description = "List calendars."

    def execute(self, args):
        """Return all calendar containers."""

        rows = self.context.require("calendar").listCalendars()
        return self.ok(format_result(rows))
