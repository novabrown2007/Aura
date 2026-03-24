"""Command-system implementation for `configReloadCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class ConfigReloadCommand(BaseCommand):
    """
    Reload Aura configuration from disk.
    """

    name = "reload"
    help_message = "Reload configuration from config.yml."

    def __init__(self, context):
        """Initialize `ConfigReloadCommand` with required dependencies and internal state."""
        super().__init__(context)
        if context.logger:
            self.logger = context.logger.getChild("Commands.Config.Reload")

        context.configCommandHandler.registerCommand(self)

        if self.logger:
            self.logger.info("Initialized.")

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        try:
            config = self.context.require("config")
            config.reload()
            if self.logger:
                self.logger.info("Configuration reloaded via command")
            return "Configuration reloaded."
        except Exception as error:
            if self.logger:
                self.logger.error(f"Configuration reload failed: {error}")
            return f"Configuration reload failed: {error}"

