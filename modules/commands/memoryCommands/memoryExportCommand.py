"""Command-system implementation for `memoryExportCommand` within Aura's CLI architecture."""

import json
from pathlib import Path

from modules.commands.baseCommand import BaseCommand


class MemoryExportCommand(BaseCommand):
    """Implements the `/memory-export` CLI command behavior and response generation."""
    name = "export"
    help_message = "Export memory to a JSON file."

    def __init__(self, context):
        """Initialize `MemoryExportCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        output_path = args[0] if args else "memory_export.json"

        memory = self.context.require("memoryManager").getMemory()
        path = Path(output_path)
        path.write_text(json.dumps(memory, indent=2), encoding="utf-8")

        return f"Memory exported to {path}."

