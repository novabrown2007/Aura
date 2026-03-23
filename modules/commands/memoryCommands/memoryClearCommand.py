from modules.commands.baseCommand import BaseCommand


class MemoryClearCommand(BaseCommand):
    name = "clear"
    help_message = "Clear all long-term memory."

    def __init__(self, context):
        super().__init__(context)
        context.memoryCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        self.context.require("memoryManager").clear()
        return "Memory cleared."

