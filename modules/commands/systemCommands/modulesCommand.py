from modules.commands.baseCommand import BaseCommand


class ModulesCommand(BaseCommand):
    """
    Lists loaded modules.
    """

    name = "modules"
    help_message = "List loaded modules."

    def __init__(self, context):
        super().__init__(context)
        context.systemCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
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
