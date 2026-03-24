"""LLM debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class LlmDebugCommand(BaseCommand):
    """Show LLM runtime settings."""

    path = ("debug", "llm")
    description = "Show LLM debug information."

    def execute(self, args):
        """Return basic LLM diagnostics."""

        config = self.context.require("config")
        lines = [
            f"model: {config.get('llm.model')}",
            f"endpoint: {config.get('llm.endpoint')}",
            f"history_limit: {config.get('llm.history.limit')}",
        ]
        return self.ok("\n".join(lines))

