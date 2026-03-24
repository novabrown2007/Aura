"""Calendar month-view command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import format_result, parse_key_value_args


class CalendarMonthCommand(BaseCommand):
    """Build a month view from the calendar backend."""

    path = ("calendar", "month")
    description = "Show month view. Usage: /calendar month month=24/03/2026 [calendar_id=1]"

    def execute(self, args):
        """Return a month-level view."""

        fields = parse_key_value_args(args)
        if "month" not in fields:
            return self.fail("Usage: /calendar month month=24/03/2026 [calendar_id=1]")
        result = self.context.require("calendar").buildMonthView(
            month_value=fields["month"],
            calendar_id=fields.get("calendar_id"),
        )
        return self.ok(format_result(result))
