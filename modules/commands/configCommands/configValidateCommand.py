from modules.commands.baseCommand import BaseCommand


class ConfigValidateCommand(BaseCommand):
    name = "validate"
    help_message = "Validate required configuration keys."

    def __init__(self, context):
        super().__init__(context)
        context.configCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
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

