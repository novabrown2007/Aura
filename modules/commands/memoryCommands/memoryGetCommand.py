"""Memory get command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class MemoryGetCommand(BaseCommand):
    """Get one memory entry by key."""

    path = ("memory", "get")
    description = "Get one memory value. Usage: /memory get <key>"

    def execute(self, args):
        """Return one memory value."""

        if not args:
            return self.fail("Usage: /memory get <key>")
        key = args[0]
        value = self.context.require("memoryManager").get(key)
        return self.ok(f"{key} = {value!r}")

