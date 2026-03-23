"""Command-system implementation for `memoryImportCommand` within Aura's CLI architecture."""

import json
from pathlib import Path

from modules.commands.baseCommand import BaseCommand


class MemoryImportCommand(BaseCommand):
    """Implements the `/memory-import` CLI command behavior and response generation."""
    name = "import"
    help_message = "Import memory from a JSON file."

    def __init__(self, context):
        """Initialize `MemoryImportCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if not args:
            return "Usage: /memory import <path>"

        input_path = Path(args[0])
        if not input_path.exists():
            return f"Import file not found: {input_path}"

        try:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
        except Exception as error:
            return f"Failed to read import file: {error}"

        if not isinstance(payload, dict):
            return "Import file must contain a JSON object."

        manager = self.context.require("memoryManager")
        imported = 0
        for key, value in payload.items():
            if key and value is not None:
                manager.setMemory(str(key), str(value))
                imported += 1

        return f"Imported {imported} memory entries from {input_path}."

