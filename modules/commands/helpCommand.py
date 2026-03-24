"""Help command for Aura CLI."""

from __future__ import annotations

from modules.commands.baseCommand import BaseCommand


class HelpCommand(BaseCommand):
    """List registered CLI commands and their descriptions."""

    path = ("help",)
    description = "Show available CLI commands."

    def execute(self, args):
        """Return formatted command help text."""

        registry = self.context.require("commandRegistry")
        lines = ["Available commands:"]
        for command in registry.listCommands():
            lines.append(f"/{' '.join(command.path)} - {command.description}")
        return self.ok("\n".join(lines))
