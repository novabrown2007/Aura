"""Memory debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemoryDebugCommand(BaseCommand):
    """Show memory subsystem diagnostics."""

    path = ("debug", "memory")
    description = "Show memory subsystem debug information."

    def execute(self, args):
        """Return high-level memory subsystem diagnostics."""

        memory = self.context.require("memoryManager").getMemory()
        lines = [
            f"entries: {len(memory)}",
            f"keys: {', '.join(sorted(memory.keys())) if memory else 'none'}",
        ]
        return self.ok("\n".join(lines))

