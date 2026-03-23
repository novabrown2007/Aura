"""Command-system implementation for `configGetCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class ConfigGetCommand(BaseCommand):
    """Implements the `/config-get` CLI command behavior and response generation."""
    name = "get"
    help_message = "Get a config value by key path."

    def __init__(self, context):
        """Initialize `ConfigGetCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.configCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if not args:
            return "Usage: /config get <key>"

        key = args[0]
        value = self.context.require("config").get(key)
        if value is None:
            return f'Config key "{key}" was not found.'
        return f"{key} = {value}"

