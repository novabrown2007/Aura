"""Version command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class VersionCommand(BaseCommand):
    """Show a simple branch/runtime version string."""

    path = ("version",)
    description = "Show the Aura CLI branch version."

    def execute(self, args):
        """Return a lightweight version message."""

        return self.ok("Aura CLI interface branch")
