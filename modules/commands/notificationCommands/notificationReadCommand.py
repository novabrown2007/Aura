"""Notification read command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.notificationCommands._notificationCommandUtils import parse_key_value_args


class NotificationReadCommand(BaseCommand):
    """Mark one notification as read."""

    path = ("notification", "read")
    description = "Mark one notification as read. Usage: /notification read id=1"

    def execute(self, args):
        """Mark one notification as read."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /notification read id=1")

        notification_id = int(fields["id"])
        self.context.require("notifications").markRead(notification_id)
        return self.ok(f"Marked notification {notification_id} as read.")
