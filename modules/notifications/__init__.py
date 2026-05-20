"""Notifications module registration for Aura."""

from modules.notifications.notifications import Notifications


MODULE_METADATA = Notifications.metadata


def createModule(context=None):
    """Create the notifications Aura module adapter."""

    return Notifications()


def register(context):
    """
    Register the notifications service with the runtime context.

    Runtime modules can use this service for creating and reading notification
    records.
    """

    context.notifications = Notifications(context)
