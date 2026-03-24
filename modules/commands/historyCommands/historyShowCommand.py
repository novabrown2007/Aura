"""History show command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class HistoryShowCommand(BaseCommand):
    """Show recent conversation history."""

    path = ("history", "show")
    description = "Show recent conversation history. Usage: /history show [limit]"

    def execute(self, args):
        """Return recent conversation history messages."""

        limit = int(args[0]) if args else 15
        rows = self.context.require("conversationHistory").getRecentMessages(limit=limit)
        if not rows:
            return self.ok("No conversation history.")
        return self.ok("\n".join(f"{role}: {content}" for role, content in rows))

