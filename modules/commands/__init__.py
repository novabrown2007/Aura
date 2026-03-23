"""Initialize the `modules.commands` package and expose package-level integration points."""

from modules.commands.commandRegistry import CommandRegistry


def register(context):
    """
    Register command system with the runtime context.

    Called by ModuleLoader during startup.
    """

    if getattr(context, "commandHandler", None) is not None:
        return

    CommandRegistry(context)
