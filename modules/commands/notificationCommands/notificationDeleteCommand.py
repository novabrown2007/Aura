"""Notification delete command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.notificationCommands._notificationCommandUtils import parse_key_value_args


class NotificationDeleteCommand(BaseCommand):
    """Delete one notification."""

    path = ("notification", "delete")
    description = "Delete one notification. Usage: /notification delete id=1"

    def execute(self, args):
        """Delete one notification by ID."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /notification delete id=1")

        notification_id = int(fields["id"])
        self.context.require("notifications").deleteNotification(notification_id)
        return self.ok(f"Deleted notification {notification_id}.")
