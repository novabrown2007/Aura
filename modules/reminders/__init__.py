"""Reminder module registration for Aura."""

from modules.reminders.reminders import Reminders


MODULE_METADATA = Reminders.metadata


def createModule(context=None):
    """Create the reminders Aura module adapter."""

    return Reminders()


def register(context):
    """
    Register the reminders data module with the runtime context.
    """

    context.reminders = Reminders(context)
