"""Runtime debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class RuntimeDebugCommand(BaseCommand):
    """Show runtime lifecycle and interface state."""

    path = ("debug", "runtime")
    description = "Show runtime debug information."

    def execute(self, args):
        """Return a compact runtime debug dump."""

        lines = [
            f"should_exit: {self.context.should_exit}",
            f"restart_requested: {self.context.restart_requested}",
            f"modules_loaded: {len(self.context.modules)}",
            f"requests_logged: {len(self.context.inputManager.getRequests())}",
            f"responses_logged: {len(self.context.outputManager.getMessages())}",
        ]
        return self.ok("\n".join(lines))

