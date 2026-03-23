"""Command-system implementation for `memorySearchCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class MemorySearchCommand(BaseCommand):
    """Implements the `/memory-search` CLI command behavior and response generation."""
    name = "search"
    help_message = "Search memory keys and values."

    def __init__(self, context):
        """Initialize `MemorySearchCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if not args:
            return "Usage: /memory search <term>"

        term = " ".join(args).strip().lower()
        memory = self.context.require("memoryManager").getMemory()

        matches = []
        for key, value in memory.items():
            if term in key.lower() or term in str(value).lower():
                matches.append((key, value))

        if not matches:
            return f'No memory entries found for "{term}".'

        lines = [f'------ MEMORY SEARCH: "{term}" ------']
        for key, value in matches:
            lines.append(f"{key} = {value}")
        return "\n".join(lines)

