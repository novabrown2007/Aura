"""Memory list command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemoryListCommand(BaseCommand):
    """List all memory entries."""

    path = ("memory", "list")
    description = "List stored memory values."

    def execute(self, args):
        """Return all stored memory values."""

        rows = self.context.require("memoryManager").getMemory()
        if not rows:
            return self.ok("No memory stored.")
        return self.ok("\n".join(f"{key} = {value}" for key, value in sorted(rows.items())))

