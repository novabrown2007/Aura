"""System restart command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class RestartCommand(BaseCommand):
    """Request a full runtime restart."""

    path = ("system", "restart")
    description = "Restart the full Aura runtime."

    def execute(self, args):
        """Trigger a runtime restart."""

        self.context.require("system").restart()
        return self.ok("Restart requested.")

