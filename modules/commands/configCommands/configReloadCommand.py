"""Config reload command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class ConfigReloadCommand(BaseCommand):
    """Reload config from disk."""

    path = ("config", "reload")
    description = "Reload configuration from config.yml."

    def execute(self, args):
        """Delegate to the system reload action."""

        data = self.context.require("system").reload()
        return self.ok(f"Configuration reloaded. Sections: {', '.join(sorted(data.keys()))}")

