"""Registry for nested CLI commands in Aura."""

from __future__ import annotations

from typing import Iterable, Optional


class CommandRegistry:
    """
    Store and resolve command objects by nested command path.
    """

    def __init__(self):
        """Initialize an empty command registry."""

        self._commands = {}

    def register(self, command):
        """Register one command object by its declared path."""

        self._commands[tuple(command.path)] = command

    def listCommands(self) -> list:
        """Return registered command objects sorted by path."""

        return [self._commands[key] for key in sorted(self._commands.keys())]

    def resolve(self, tokens: Iterable[str]):
        """
        Resolve the longest matching command path from a token sequence.

        Returns:
            tuple[command | None, list[str]]:
                Matching command object and remaining argument tokens.
        """

        original_tokens = [str(token) for token in tokens]
        lowered_tokens = [token.lower() for token in original_tokens]
        for index in range(len(lowered_tokens), 0, -1):
            candidate_path = tuple(lowered_tokens[:index])
            command = self._commands.get(candidate_path)
            if command is not None:
                return command, original_tokens[index:]
        return None, original_tokens
