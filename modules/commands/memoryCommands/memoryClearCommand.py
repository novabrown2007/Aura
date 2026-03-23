"""Command-system implementation for `memoryClearCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class MemoryClearCommand(BaseCommand):
    """Implements the `/memory-clear` CLI command behavior and response generation."""
    name = "clear"
    help_message = "Clear all long-term memory."

    def __init__(self, context):
        """Initialize `MemoryClearCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        self.context.require("memoryManager").clear()
        return "Memory cleared."

