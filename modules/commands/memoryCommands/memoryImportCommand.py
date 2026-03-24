"""Memory import command for Aura CLI."""

import json
from pathlib import Path

from modules.commands.baseCommand import BaseCommand


class MemoryImportCommand(BaseCommand):
    """Import memory values from a JSON file."""

    path = ("memory", "import")
    description = "Import memory from JSON. Usage: /memory import <path>"

    def execute(self, args):
        """Read memory entries from disk and persist them."""

        if not args:
            return self.fail("Usage: /memory import <path>")
        input_path = Path(args[0])
        with open(input_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        manager = self.context.require("memoryManager")
        for key, value in dict(data).items():
            manager.setMemory(str(key), str(value))
        return self.ok(f"Imported memory from {input_path}")

