"""Reminders debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class RemindersDebugCommand(BaseCommand):
    """Show shared reminders subsystem diagnostics."""

    path = ("debug", "reminders")
    description = "Show shared reminders subsystem debug information."

    def execute(self, args):
        """Return high-level reminder diagnostics."""

        reminders = self.context.require("reminders").listReminders()
        unsent_rows = [row for row in reminders if row.get("sent_at") in {None, ""}]
        next_due = None
        scheduled_rows = [row for row in reminders if row.get("reminder_at")]
        if scheduled_rows:
            next_due = min(str(row["reminder_at"]) for row in scheduled_rows)
        lines = [
            f"entries: {len(reminders)}",
            f"unsent: {len(unsent_rows)}",
            f"next_due: {next_due or 'none'}",
        ]
        return self.ok("\n".join(lines))
