"""Command-system implementation for `versionCommand` within Aura's CLI architecture."""

import platform

from modules.commands.baseCommand import BaseCommand


class VersionCommand(BaseCommand):
    """Implements the `/version` CLI command behavior and response generation."""
    name = "version"
    help_message = "Show Aura build/version information."

    def __init__(self, context):
        """Initialize `VersionCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.commandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        return (
            "Aura version: Development Build\n"
            f"Python: {platform.python_version()}"
        )

