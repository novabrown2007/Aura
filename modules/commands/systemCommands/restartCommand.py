from modules.commands.baseCommand import BaseCommand


class RestartCommand(BaseCommand):
    """
    Requests a restart of Aura.
    """

    name = "restart"
    help_message = "Request Aura restart."

    def __init__(self, context):
        super().__init__(context)
        context.systemCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        self.context.should_restart = True
        self.context.should_exit = True
        return "Restart requested. Shutting down Aura..."

