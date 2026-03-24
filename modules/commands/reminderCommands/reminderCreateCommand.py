"""Reminder creation command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.reminderCommands._reminderCommandUtils import parse_key_value_args


class ReminderCreateCommand(BaseCommand):
    """Create a shared reminder row."""

    path = ("reminder", "create")
    description = (
        "Create a reminder. Usage: /reminder create title='Take meds' "
        "content='After dinner' module=system remind_at='19:00 24/03/2026'"
    )

    def execute(self, args):
        """Create a reminder from key=value arguments."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        required_keys = {"title", "content", "module"}
        missing_keys = [key for key in required_keys if key not in fields]
        if missing_keys:
            return self.fail(
                "Usage: /reminder create title='Take meds' content='After dinner' "
                "module=system [remind_at='19:00 24/03/2026']"
            )

        reminder_id = self.context.require("reminders").createReminder(
            title=fields["title"],
            content=fields["content"],
            module_of_origin=fields["module"],
            reminder_at=fields.get("remind_at"),
        )
        return self.ok(f"Created reminder {reminder_id}: {fields['title']}")
