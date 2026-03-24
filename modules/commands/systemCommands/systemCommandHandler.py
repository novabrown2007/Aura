"""System command registration for Aura CLI."""

from modules.commands.systemCommands.modulesCommand import ModulesCommand
from modules.commands.systemCommands.restartCommand import RestartCommand
from modules.commands.systemCommands.shutdownCommand import ShutdownCommand
from modules.commands.systemCommands.tasksCommand import TasksCommand


def build_commands(context):
    """Return the system command objects for registry registration."""

    return [
        ModulesCommand(context),
        RestartCommand(context),
        ShutdownCommand(context),
        TasksCommand(context),
    ]
