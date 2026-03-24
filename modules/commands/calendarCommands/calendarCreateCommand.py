"""Calendar create command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.calendarCommands._calendarCommandUtils import parse_key_value_args


class CalendarCreateCommand(BaseCommand):
    """Create a calendar container."""

    path = ("calendar", "create")
    description = "Create a calendar. Usage: /calendar create name=Work [description=...] [color=#3ea6ff] [timezone=UTC] [visibility=private] [is_default=true]"

    def execute(self, args):
        """Create a new calendar from key=value arguments."""

        fields = parse_key_value_args(args)
        if "name" not in fields:
            return self.fail("Usage: /calendar create name=Work [description=...] [color=...] [timezone=...]")
        self.context.require("calendar").createCalendar(**fields)
        return self.ok(f"Created calendar: {fields['name']}")
