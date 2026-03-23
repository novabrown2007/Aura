"""Command-system implementation for `configSetCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class ConfigSetCommand(BaseCommand):
    """Implements the `/config-set` CLI command behavior and response generation."""
    name = "set"
    help_message = "Set an in-memory config value by key path."

    def __init__(self, context):
        """Initialize `ConfigSetCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.configCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if len(args) < 2:
            return "Usage: /config set <key> <value>"

        key = args[0]
        value = " ".join(args[1:])
        config = self.context.require("config")

        if hasattr(config, "asDict"):
            data = config.asDict()
        elif hasattr(config, "data"):
            data = config.data
        elif hasattr(config, "_data"):
            data = config._data
        else:
            return "Configuration backend does not support updates."

        parts = key.split(".")
        node = data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

        return f"Config updated (runtime): {key} = {value}"
