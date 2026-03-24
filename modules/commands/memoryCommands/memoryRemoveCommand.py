"""Memory remove command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemoryRemoveCommand(BaseCommand):
    """Delete one memory entry."""

    path = ("memory", "remove")
    description = "Remove one memory value. Usage: /memory remove <key>"

    def execute(self, args):
        """Delete one memory key."""

        if not args:
            return self.fail("Usage: /memory remove <key>")
        self.context.require("memoryManager").delete(args[0])
        return self.ok(f"Removed memory: {args[0]}")

