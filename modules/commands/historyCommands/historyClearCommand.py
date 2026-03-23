"""Command-system implementation for `historyClearCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class HistoryClearCommand(BaseCommand):
    """Implements the `/history-clear` CLI command behavior and response generation."""
    name = "clear"
    help_message = "Clear short-term conversation history."

    def __init__(self, context):
        """Initialize `HistoryClearCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.historyCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        self.context.require("conversationHistory").clear()
        return "Conversation history cleared."

