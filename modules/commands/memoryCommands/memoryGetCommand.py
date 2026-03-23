from modules.commands.baseCommand import BaseCommand


class MemoryGetCommand(BaseCommand):
    name = "get"
    help_message = "Get one memory value by key."

    def __init__(self, context):
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        if not args:
            return "Usage: /memory get <key>"

        key = args[0]
        value = self.context.require("memoryManager").get(key)
        if value is None:
            return f'Memory key "{key}" does not exist.'
        return f"{key} = {value}"

