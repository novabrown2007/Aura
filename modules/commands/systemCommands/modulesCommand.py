"""Command-system implementation for `modulesCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class ModulesCommand(BaseCommand):
    """
    Lists loaded modules.
    """

    name = "modules"
    help_message = "List loaded modules."

    def __init__(self, context):
        """Initialize `ModulesCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.systemCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if args and args[0].lower() != "list":
            return "Usage: /system modules list"

        if hasattr(self.context, "listModules"):
            module_names = self.context.listModules()
        else:
            module_names = list(getattr(self.context, "modules", {}).keys())
        if not module_names:
            return "No modules are currently registered."

        lines = ["------ MODULES ------"]
        lines.extend(module_names)
        return "\n".join(lines)
