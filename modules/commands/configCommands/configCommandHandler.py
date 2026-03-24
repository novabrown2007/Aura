"""Config command registration for Aura CLI."""

from modules.commands.configCommands.configGetCommand import ConfigGetCommand
from modules.commands.configCommands.configReloadCommand import ConfigReloadCommand
from modules.commands.configCommands.configSetCommand import ConfigSetCommand
from modules.commands.configCommands.configValidateCommand import ConfigValidateCommand


def build_commands(context):
    """Return the config command objects for registry registration."""

    return [
        ConfigGetCommand(context),
        ConfigReloadCommand(context),
        ConfigSetCommand(context),
        ConfigValidateCommand(context),
    ]
