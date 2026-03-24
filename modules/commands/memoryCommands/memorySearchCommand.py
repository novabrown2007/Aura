"""Memory search command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemorySearchCommand(BaseCommand):
    """Search stored memory values."""

    path = ("memory", "search")
    description = "Search stored memory. Usage: /memory search <text>"

    def execute(self, args):
        """Search memory keys and values for one text fragment."""

        if not args:
            return self.fail("Usage: /memory search <text>")
        query = " ".join(args).lower()
        rows = self.context.require("memoryManager").getMemory()
        matches = {
            key: value for key, value in rows.items()
            if query in key.lower() or query in str(value).lower()
        }
        if not matches:
            return self.ok("No matching memory entries.")
        return self.ok("\n".join(f"{key} = {value}" for key, value in sorted(matches.items())))

