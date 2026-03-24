"""Calendar day-view command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import format_result, parse_key_value_args


class CalendarDayCommand(BaseCommand):
    """Build a day view from the calendar backend."""

    path = ("calendar", "day")
    description = "Show day view. Usage: /calendar day day=24/03/2026 [calendar_id=1]"

    def execute(self, args):
        """Return a day-level view."""

        fields = parse_key_value_args(args)
        if "day" not in fields:
            return self.fail("Usage: /calendar day day=24/03/2026 [calendar_id=1]")
        result = self.context.require("calendar").buildDayView(
            day=fields["day"],
            calendar_id=fields.get("calendar_id"),
        )
        return self.ok(format_result(result))
