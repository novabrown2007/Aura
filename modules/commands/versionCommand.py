import platform

from modules.commands.baseCommand import BaseCommand


class VersionCommand(BaseCommand):
    name = "version"
    help_message = "Show Aura build/version information."

    def __init__(self, context):
        super().__init__(context)
        context.commandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        return (
            "Aura version: Development Build\n"
            f"Python: {platform.python_version()}"
        )

