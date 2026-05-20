"""Calendar module registration for Aura."""

from modules.calendar.calendar import Calendar


MODULE_METADATA = Calendar.metadata


def createModule(context=None):
    """Create the calendar Aura module adapter."""

    return Calendar()


def register(context):
    """
    Register the calendar module with the runtime context.

    This function is called by ModuleLoader at startup so the calendar
    backend becomes available to the runtime.
    """

    context.calendar = Calendar(context)
