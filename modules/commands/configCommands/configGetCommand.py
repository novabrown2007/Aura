from modules.commands.baseCommand import BaseCommand


class ConfigGetCommand(BaseCommand):
    name = "get"
    help_message = "Get a config value by key path."

    def __init__(self, context):
        super().__init__(context)
        context.configCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        if not args:
            return "Usage: /config get <key>"

        key = args[0]
        value = self.context.require("config").get(key)
        if value is None:
            return f'Config key "{key}" was not found.'
        return f"{key} = {value}"

