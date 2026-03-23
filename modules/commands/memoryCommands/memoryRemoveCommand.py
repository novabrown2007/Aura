from modules.commands.baseCommand import BaseCommand


class MemoryRemoveCommand(BaseCommand):
    name = "remove"
    help_message = "Remove a memory key."

    def __init__(self, context):
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        if not args:
            return "Usage: /memory remove <key>"

        key = args[0]
        manager = self.context.require("memoryManager")
        existing = manager.get(key)
        if existing is None:
            return f'Memory key "{key}" does not exist.'

        manager.delete(key)
        return f"Memory removed: {key}"

