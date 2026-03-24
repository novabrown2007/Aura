"""Reminder command registration for Aura CLI."""

from modules.commands.reminderCommands.reminderCreateCommand import ReminderCreateCommand
from modules.commands.reminderCommands.reminderDeleteCommand import ReminderDeleteCommand
from modules.commands.reminderCommands.reminderGetCommand import ReminderGetCommand
from modules.commands.reminderCommands.reminderListCommand import ReminderListCommand


def build_commands(context):
    """Return the reminder command objects for registry registration."""

    return [
        ReminderCreateCommand(context),
        ReminderGetCommand(context),
        ReminderListCommand(context),
        ReminderDeleteCommand(context),
    ]
