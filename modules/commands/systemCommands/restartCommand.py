"""Command-system implementation for `restartCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class RestartCommand(BaseCommand):
    """
    Requests a restart of Aura.
    """

    name = "restart"
    help_message = "Request Aura restart."

    def __init__(self, context):
        """Initialize `RestartCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.systemCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        self.context.should_restart = True
        self.context.should_exit = True
        return "Restart requested. Shutting down Aura..."

