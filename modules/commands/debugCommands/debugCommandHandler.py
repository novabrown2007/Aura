"""Debug command registration for Aura CLI."""

from modules.commands.debugCommands.calendarDebugCommand import CalendarDebugCommand
from modules.commands.debugCommands.databaseDebugCommands import DatabaseDebugCommand
from modules.commands.debugCommands.llmDebugCommand import LlmDebugCommand
from modules.commands.debugCommands.logsDebugCommand import LogsDebugCommand
from modules.commands.debugCommands.memoryDebugCommands import MemoryDebugCommand
from modules.commands.debugCommands.notificationsDebugCommand import NotificationsDebugCommand
from modules.commands.debugCommands.remindersDebugCommand import RemindersDebugCommand
from modules.commands.debugCommands.runtimeDebugCommand import RuntimeDebugCommand
from modules.commands.debugCommands.threadingDebugCommand import ThreadingDebugCommand


def build_commands(context):
    """Return the debug command objects for registry registration."""

    return [
        RuntimeDebugCommand(context),
        DatabaseDebugCommand(context),
        CalendarDebugCommand(context),
        LlmDebugCommand(context),
        LogsDebugCommand(context),
        MemoryDebugCommand(context),
        NotificationsDebugCommand(context),
        RemindersDebugCommand(context),
        ThreadingDebugCommand(context),
    ]
