"""Command-system implementation for `memoryGetCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class MemoryGetCommand(BaseCommand):
    """Implements the `/memory-get` CLI command behavior and response generation."""
    name = "get"
    help_message = "Get one memory value by key."

    def __init__(self, context):
        """Initialize `MemoryGetCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if not args:
            return "Usage: /memory get <key>"

        key = args[0]
        value = self.context.require("memoryManager").get(key)
        if value is None:
            return f'Memory key "{key}" does not exist.'
        return f"{key} = {value}"

