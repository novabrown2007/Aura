"""History clear command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class HistoryClearCommand(BaseCommand):
    """Clear stored conversation history."""

    path = ("history", "clear")
    description = "Clear conversation history."

    def execute(self, args):
        """Clear the stored conversation history."""

        self.context.require("conversationHistory").clear()
        return self.ok("Conversation history cleared.")

