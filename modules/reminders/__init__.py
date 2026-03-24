"""Reminder module registration for Aura."""

from modules.reminders.reminders import Reminders


def register(context):
    """
    Register the reminders data module with the runtime context.
    """

    context.reminders = Reminders(context)
