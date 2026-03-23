"""Command-system implementation for `memorySetCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class MemorySetCommand(BaseCommand):
    """Implements the `/memory-set` CLI command behavior and response generation."""
    name = "set"
    help_message = "Set a long-term memory key/value pair."

    def __init__(self, context):
        """Initialize `MemorySetCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if len(args) < 2:
            return 'Usage: /memory set <key> "<value>"'

        key = args[0]
        raw_value = " ".join(args[1:]).strip()

        if raw_value.startswith('"') and raw_value.endswith('"'):
            value = raw_value[1:-1]
        else:
            value = raw_value

        self.context.require("memoryManager").setMemory(key, value)
        return f'Memory set: {key} = "{value}"'

