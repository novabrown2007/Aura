"""Notification lookup command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand
from modules.commands.notificationCommands._notificationCommandUtils import format_result, parse_key_value_args


class NotificationGetCommand(BaseCommand):
    """Fetch one notification by ID."""

    path = ("notification", "get")
    description = "Get one notification. Usage: /notification get id=1"

    def execute(self, args):
        """Return one notification row."""

        try:
            fields = parse_key_value_args(args)
        except ValueError as error:
            return self.fail(str(error))

        if "id" not in fields:
            return self.fail("Usage: /notification get id=1")

        notification = self.context.require("notifications").getNotification(int(fields["id"]))
        return self.ok(format_result(notification))
