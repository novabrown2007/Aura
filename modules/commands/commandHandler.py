"""CLI command parsing and dispatch for Aura."""

from __future__ import annotations

import shlex

from modules.commands.baseCommand import CommandResult
from modules.commands.calendarCommands.calendarCommandHandler import build_commands as build_calendar_commands
from modules.commands.commandRegistry import CommandRegistry
from modules.commands.configCommands.configCommandHandler import build_commands as build_config_commands
from modules.commands.debugCommands.debugCommandHandler import build_commands as build_debug_commands
from modules.commands.helpCommand import HelpCommand
from modules.commands.historyCommands.historyCommandHandler import build_commands as build_history_commands
from modules.commands.memoryCommands.memoryCommandHandler import build_commands as build_memory_commands
from modules.commands.reminderCommands.reminderCommandHandler import build_commands as build_reminder_commands
from modules.commands.statusCommand import StatusCommand
from modules.commands.systemCommands.systemCommandHandler import build_commands as build_system_commands
from modules.commands.versionCommand import VersionCommand


class CommandHandler:
    """
    Resolve and execute slash commands for the CLI branch.
    """

    def __init__(self, context):
        """Build a registry of available CLI commands."""

        self.context = context
        self.logger = context.logger.getChild("CLI.CommandHandler") if context.logger else None
        self.registry = CommandRegistry()
        self._registerDefaults()

    def _registerDefaults(self):
        """Register the built-in CLI commands."""

        commands = [
            HelpCommand(self.context),
            StatusCommand(self.context),
            VersionCommand(self.context),
            *build_calendar_commands(self.context),
            *build_config_commands(self.context),
            *build_debug_commands(self.context),
            *build_history_commands(self.context),
            *build_memory_commands(self.context),
            *build_reminder_commands(self.context),
            *build_system_commands(self.context),
        ]
        for command in commands:
            self.registry.register(command)

    def isCommand(self, text: str) -> bool:
        """Return whether the text is a slash command."""

        return str(text).strip().startswith("/")

    def handle(self, text: str) -> CommandResult:
        """Execute one CLI slash command."""

        raw_value = str(text).strip()
        if not raw_value.startswith("/"):
            return CommandResult(success=False, message="Not a command.")

        tokens = shlex.split(raw_value[1:])
        if not tokens:
            return CommandResult(success=False, message="Empty command.")

        command, args = self.registry.resolve(tokens)
        if command is None:
            return CommandResult(success=False, message=f"Unknown command: /{' '.join(tokens)}")

        if self.logger:
            self.logger.info(f"Executing command: /{' '.join(tokens)}")
        return command.execute(args)
