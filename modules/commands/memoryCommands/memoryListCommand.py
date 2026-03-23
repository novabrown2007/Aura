"""Command-system implementation for `memoryListCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class MemoryListCommand(BaseCommand):
    """Implements the `/memory-list` CLI command behavior and response generation."""
    name = "list"
    help_message = "List all long-term memory entries."

    def __init__(self, context):
        """Initialize `MemoryListCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        memory = self.context.require("memoryManager").getMemory()
        if not memory:
            return "Memory is empty."

        lines = ["------ MEMORY ------"]
        for key, value in memory.items():
            lines.append(f"{key} = {value}")
        return "\n".join(lines)

