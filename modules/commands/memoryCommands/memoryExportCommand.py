import json
from pathlib import Path

from modules.commands.baseCommand import BaseCommand


class MemoryExportCommand(BaseCommand):
    name = "export"
    help_message = "Export memory to a JSON file."

    def __init__(self, context):
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        output_path = args[0] if args else "memory_export.json"

        memory = self.context.require("memoryManager").getMemory()
        path = Path(output_path)
        path.write_text(json.dumps(memory, indent=2), encoding="utf-8")

        return f"Memory exported to {path}."

