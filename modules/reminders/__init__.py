"""Reminder module registration for Aura."""

from modules.reminders.reminderCommands import ReminderCommands
from modules.reminders.reminders import Reminders


def register(context):
    """
    Register the reminders module and reminder command handler.

    This function is called by ModuleLoader at startup.
    """

    context.reminders = Reminders(context)

    if getattr(context, "commandHandler", None) is None:
        logger = getattr(context, "logger", None)
        if logger:
            logger.getChild("Reminders").warning(
                "CommandHandler is unavailable; /reminder commands were not registered."
            )
        return

    context.reminderCommands = ReminderCommands(context)

