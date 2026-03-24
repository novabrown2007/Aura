"""Config set command for Aura CLI."""

from pathlib import Path
import yaml

from modules.commands.baseCommand import BaseCommand


class ConfigSetCommand(BaseCommand):
    """Update one config value in config.yml."""

    path = ("config", "set")
    description = "Set one config value. Usage: /config set <key> <value>"

    def execute(self, args):
        """Update a config key both on disk and in memory."""

        if len(args) < 2:
            return self.fail("Usage: /config set <key> <value>")

        key = args[0]
        raw_value = " ".join(args[1:])
        parsed_value = yaml.safe_load(raw_value)

        path = Path("config.yml")
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        target = data
        parts = key.split(".")
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = parsed_value

        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, sort_keys=False)

        self.context.config.reload()
        return self.ok(f"Updated config key: {key}")

