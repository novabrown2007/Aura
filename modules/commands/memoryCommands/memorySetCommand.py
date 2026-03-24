"""Memory set command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemorySetCommand(BaseCommand):
    """Set one memory entry."""

    path = ("memory", "set")
    description = "Set one memory value. Usage: /memory set <key> <value>"

    def execute(self, args):
        """Persist one memory key/value pair."""

        if len(args) < 2:
            return self.fail("Usage: /memory set <key> <value>")
        key = args[0]
        value = " ".join(args[1:])
        self.context.require("memoryManager").setMemory(key, value)
        return self.ok(f"Stored memory: {key}")

