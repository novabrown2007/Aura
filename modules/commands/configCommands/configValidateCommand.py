"""Command-system implementation for `configValidateCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class ConfigValidateCommand(BaseCommand):
    """Implements the `/config-validate` CLI command behavior and response generation."""
    name = "validate"
    help_message = "Validate required configuration keys."

    def __init__(self, context):
        """Initialize `ConfigValidateCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.configCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        config = self.context.require("config")
        required_keys = [
            "llm.endpoint",
            "llm.model",
            "database.host",
            "database.port",
            "database.name",
            "database.user",
            "database.password",
        ]

        missing = [key for key in required_keys if config.get(key) is None]
        if missing:
            lines = ["Configuration validation failed. Missing keys:"]
            lines.extend([f"- {key}" for key in missing])
            return "\n".join(lines)

        return "Configuration validation passed."

