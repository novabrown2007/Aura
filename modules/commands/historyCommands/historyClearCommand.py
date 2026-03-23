from modules.commands.baseCommand import BaseCommand


class HistoryClearCommand(BaseCommand):
    name = "clear"
    help_message = "Clear short-term conversation history."

    def __init__(self, context):
        super().__init__(context)
        context.historyCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        self.context.require("conversationHistory").clear()
        return "Conversation history cleared."

