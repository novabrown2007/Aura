"""Config get command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class ConfigGetCommand(BaseCommand):
    """Read one configuration value using dot notation."""

    path = ("config", "get")
    description = "Read one config value. Usage: /config get <key>"

    def execute(self, args):
        """Return the requested config value."""

        if not args:
            return self.fail("Usage: /config get <key>")
        key = args[0]
        value = self.context.config.get(key)
        return self.ok(f"{key} = {value!r}")

