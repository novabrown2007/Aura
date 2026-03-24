"""Config validate command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class ConfigValidateCommand(BaseCommand):
    """Validate basic required configuration keys."""

    path = ("config", "validate")
    description = "Validate required config keys."

    REQUIRED_KEYS = (
        "llm.model",
        "llm.endpoint",
        "database.host",
        "database.port",
        "database.name",
        "database.user",
        "database.password",
    )

    def execute(self, args):
        """Return missing required config keys, if any."""

        missing = [key for key in self.REQUIRED_KEYS if self.context.config.get(key) in (None, "")]
        if missing:
            return self.fail("Missing config keys:\n" + "\n".join(missing))
        return self.ok("Configuration looks valid.")

