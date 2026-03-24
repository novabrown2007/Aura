"""Memory export command for Aura CLI."""

import json
from pathlib import Path

from modules.commands.baseCommand import BaseCommand


class MemoryExportCommand(BaseCommand):
    """Export memory to a JSON file."""

    path = ("memory", "export")
    description = "Export memory to JSON. Usage: /memory export [path]"

    def execute(self, args):
        """Write memory contents to disk."""

        output_path = Path(args[0]) if args else Path("memory_export.json")
        rows = self.context.require("memoryManager").getMemory()
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, sort_keys=True)
        return self.ok(f"Exported memory to {output_path}")

