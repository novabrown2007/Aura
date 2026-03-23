"""Command-system implementation for `historyShowCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class HistoryShowCommand(BaseCommand):
    """Implements the `/history-show` CLI command behavior and response generation."""
    name = "show"
    help_message = "Show recent short-term conversation history."

    def __init__(self, context):
        """Initialize `HistoryShowCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.historyCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        limit = 15
        if args:
            try:
                limit = max(1, int(args[0]))
            except ValueError:
                return "Usage: /history show [limit]"

        history = self.context.require("conversationHistory").getRecentMessages(limit=limit)
        if not history:
            return "Conversation history is empty."

        lines = ["------ HISTORY ------"]
        for role, content in history:
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

