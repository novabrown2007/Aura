"""Calendar debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class CalendarDebugCommand(BaseCommand):
    """Show calendar subsystem diagnostics."""

    path = ("debug", "calendar")
    description = "Show calendar subsystem debug information."

    def execute(self, args):
        """Return high-level calendar diagnostics."""

        calendar = self.context.require("calendar")
        calendars = calendar.listCalendars()
        tasks = calendar.listTasks()
        reminders = calendar.listReminders()
        lines = [
            f"calendars: {len(calendars)}",
            f"tasks: {len(tasks)}",
            f"reminders: {len(reminders)}",
            f"default_timezone: {calendar.getCalendarTimezone()}",
        ]
        return self.ok("\n".join(lines))
