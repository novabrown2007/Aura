"""Notifications module registration for Aura."""

from modules.notifications.notifications import Notifications


def register(context):
    """
    Register the notifications service with the runtime context.

    Interfaces can use this service as a backend API for creating and reading
    notification records without depending on any specific frontend.
    """

    context.notifications = Notifications(context)
