"""Notification command registration for Aura CLI."""

from modules.commands.notificationCommands.notificationDeleteCommand import NotificationDeleteCommand
from modules.commands.notificationCommands.notificationDismissCommand import NotificationDismissCommand
from modules.commands.notificationCommands.notificationGetCommand import NotificationGetCommand
from modules.commands.notificationCommands.notificationListCommand import NotificationListCommand
from modules.commands.notificationCommands.notificationReadCommand import NotificationReadCommand
from modules.commands.notificationCommands.notificationSendCommand import NotificationSendCommand


def build_commands(context):
    """Return the notification command objects for registry registration."""

    return [
        NotificationGetCommand(context),
        NotificationListCommand(context),
        NotificationSendCommand(context),
        NotificationReadCommand(context),
        NotificationDismissCommand(context),
        NotificationDeleteCommand(context),
    ]
