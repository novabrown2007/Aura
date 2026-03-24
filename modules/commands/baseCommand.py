"""Base command definitions for Aura's CLI interface branch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass
class CommandResult:
    """Structured result returned by CLI command handlers."""

    success: bool
    message: str


class BaseCommand:
    """
    Base class for CLI command handlers.

    Concrete commands expose a stable command path and a one-line description.
    The CLI branch resolves slash commands through these objects before falling
    back to normal assistant chat.
    """

    path: tuple[str, ...] = ()
    description: str = ""

    def __init__(self, context):
        """Store runtime context and optional child logger."""

        self.context = context
        self.logger = context.logger.getChild(f"CLI.Command.{'.'.join(self.path)}") if context.logger else None

    def execute(self, args: Sequence[str]) -> CommandResult:
        """Execute the command using CLI-supplied arguments."""

        raise NotImplementedError

    @staticmethod
    def ok(message: str) -> CommandResult:
        """Return a successful command result."""

        return CommandResult(success=True, message=str(message))

    @staticmethod
    def fail(message: str) -> CommandResult:
        """Return a failed command result."""

        return CommandResult(success=False, message=str(message))
