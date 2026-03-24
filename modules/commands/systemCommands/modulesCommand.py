"""System modules command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class ModulesCommand(BaseCommand):
    """List loaded runtime modules."""

    path = ("system", "modules")
    description = "List loaded modules."

    def execute(self, args):
        """Return the loaded module names."""

        modules = sorted(self.context.modules.keys())
        return self.ok("Loaded modules:\n" + ("\n".join(modules) if modules else "none"))

