from modules.commands.baseCommand import BaseCommand


class ConfigReloadCommand(BaseCommand):
    """
    Reload Aura configuration from disk.
    """

    name = "reload"
    help_message = "Reload configuration from config/config.yml."

    def __init__(self, context):
        super().__init__(context)
        if context.logger:
            self.logger = context.logger.getChild("Commands.Config.Reload")

        context.configCommandHandler.registerCommand(self)

        if self.logger:
            self.logger.info("Initialized.")

    def execute(self, args: list[str]) -> str:
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

