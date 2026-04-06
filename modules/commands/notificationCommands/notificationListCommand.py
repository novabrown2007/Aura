"""Notification list command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.notificationCommands._notificationCommandUtils import format_result, parse_key_value_args


class NotificationListCommand(BaseCommand):
    """List queued notifications."""

    path = ("notification", "list")
    description = "List notifications. Usage: /notification list [status=pending] [limit=10]"

    def execute(self, args):
        """Return notification rows with optional status and limit filters."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        rows = self.context.require("notifications").listNotifications(
            status=fields.get("status"),
            limit=fields.get("limit"),
        )
        return self.ok(format_result(rows))
