"""Calendar module registration for Aura."""

from modules.calendar.calendar import Calendar


def register(context):
    """
    Register the calendar module with the runtime context.

    This function is called by ModuleLoader at startup so the calendar
    backend becomes available to the runtime.
    """

    context.calendar = Calendar(context)
