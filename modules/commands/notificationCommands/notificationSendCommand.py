"""Notification send command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.notificationCommands._notificationCommandUtils import parse_key_value_args


class NotificationSendCommand(BaseCommand):
    """Deliver one notification immediately."""

    path = ("notification", "send")
    description = "Send one notification now. Usage: /notification send id=1"

    def execute(self, args):
        """Send one notification and return a compact status message."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /notification send id=1")

        notification_id = int(fields["id"])
        self.context.require("notifications").sendNotification(notification_id)
        return self.ok(f"Sent notification {notification_id}.")
