"""Memory command registration for Aura CLI."""

from modules.commands.memoryCommands.memoryClearCommand import MemoryClearCommand
from modules.commands.memoryCommands.memoryExportCommand import MemoryExportCommand
from modules.commands.memoryCommands.memoryGetCommand import MemoryGetCommand
from modules.commands.memoryCommands.memoryImportCommand import MemoryImportCommand
from modules.commands.memoryCommands.memoryListCommand import MemoryListCommand
from modules.commands.memoryCommands.memoryRemoveCommand import MemoryRemoveCommand
from modules.commands.memoryCommands.memorySearchCommand import MemorySearchCommand
from modules.commands.memoryCommands.memorySetCommand import MemorySetCommand


def build_commands(context):
    """Return the memory command objects for registry registration."""

    return [
        MemoryGetCommand(context),
        MemorySetCommand(context),
        MemoryRemoveCommand(context),
        MemoryListCommand(context),
        MemorySearchCommand(context),
        MemoryClearCommand(context),
        MemoryExportCommand(context),
        MemoryImportCommand(context),
    ]
