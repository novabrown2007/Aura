"""System shutdown command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class ShutdownCommand(BaseCommand):
    """Request runtime shutdown."""

    path = ("system", "shutdown")
    description = "Shutdown the Aura runtime."

    def execute(self, args):
        """Trigger runtime shutdown."""

        self.context.require("system").shutdown()
        return self.ok("Shutdown requested.")

