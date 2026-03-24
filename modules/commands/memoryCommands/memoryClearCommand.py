"""Memory clear command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemoryClearCommand(BaseCommand):
    """Clear all stored memory."""

    path = ("memory", "clear")
    description = "Clear all stored memory."

    def execute(self, args):
        """Delete all memory entries."""

        self.context.require("memoryManager").clear()
        return self.ok("All memory cleared.")

