"""Command-system implementation for `memoryRemoveCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class MemoryRemoveCommand(BaseCommand):
    """Implements the `/memory-remove` CLI command behavior and response generation."""
    name = "remove"
    help_message = "Remove a memory key."

    def __init__(self, context):
        """Initialize `MemoryRemoveCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if not args:
            return "Usage: /memory remove <key>"

        key = args[0]
        manager = self.context.require("memoryManager")
        existing = manager.get(key)
        if existing is None:
            return f'Memory key "{key}" does not exist.'

        manager.delete(key)
        return f"Memory removed: {key}"

