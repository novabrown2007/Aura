"""Notification dismiss command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.notificationCommands._notificationCommandUtils import parse_key_value_args


class NotificationDismissCommand(BaseCommand):
    """Mark one notification as dismissed."""

    path = ("notification", "dismiss")
    description = "Dismiss one notification. Usage: /notification dismiss id=1"

    def execute(self, args):
        """Mark one notification as dismissed."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /notification dismiss id=1")

        notification_id = int(fields["id"])
        self.context.require("notifications").dismissNotification(notification_id)
        return self.ok(f"Dismissed notification {notification_id}.")
