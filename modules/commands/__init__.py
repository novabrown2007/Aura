"""CLI command module registration for Aura."""

from modules.commands.commandHandler import CommandHandler


def register(context):
    """
    Register the CLI command handler and registry in the runtime context.
    """

    handler = CommandHandler(context)
    context.commandHandler = handler
    context.commandRegistry = handler.registry
