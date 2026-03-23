"""Reminder command routing for /reminder commands."""


class ReminderCommands:
    """
    Handles /reminder commands and forwards operations to Reminders.
    """

    name = "reminder"

    def __init__(self, context):
        """
        Initialize reminder command routing and register with CommandHandler.
        """

        self.context = context
        self.reminders = context.reminders

        self.logger = None
        if context.logger:
            self.logger = context.logger.getChild("Commands.Reminder")

        context.commandHandler.registerHandler(self.name, self)

        if self.logger:
            self.logger.info("Initialized.")

    def handle(self, parts: list[str], original: str = "") -> str:
        """
        Route /reminder commands.

        Supported:
        - /reminder add <title> [remind_at]
        - /reminder list
        - /reminder delete <id>
        """

        if not parts:
            return self._usage()

        action = parts[0].lower()

        if action == "add":
            if len(parts) < 2:
                return "Usage: /reminder add <title> [remind_at]"

            title = parts[1]
            remind_at = parts[2] if len(parts) >= 3 else None
            self.reminders.createReminder(title=title, remind_at=remind_at)
            return f'Reminder created: "{title}"'

        if action == "list":
            rows = self.reminders.listReminders()
            if not rows:
                return "No reminders found."

            lines = ["------ REMINDERS ------"]
            for row in rows:
                reminder_id = row.get("id")
                title = row.get("title")
                remind_at = row.get("remind_at") or "unscheduled"
                lines.append(f"{reminder_id}: {title} (at: {remind_at})")
            return "\n".join(lines)

        if action == "delete":
            if len(parts) < 2:
                return "Usage: /reminder delete <id>"
            try:
                reminder_id = int(parts[1])
            except ValueError:
                return "Usage: /reminder delete <id>"

            self.reminders.deleteReminder(reminder_id)
            return f"Reminder deleted: {reminder_id}"

        return self._usage()

    @staticmethod
    def _usage() -> str:
        """
        Return usage text for reminder commands.
        """

        return (
            "Usage:\n"
            "/reminder add <title> [remind_at]\n"
            "/reminder list\n"
            "/reminder delete <id>"
        )

