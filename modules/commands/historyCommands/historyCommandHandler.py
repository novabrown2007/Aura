"""History command registration for Aura CLI."""

from modules.commands.historyCommands.historyClearCommand import HistoryClearCommand
from modules.commands.historyCommands.historyShowCommand import HistoryShowCommand


def build_commands(context):
    """Return the history command objects for registry registration."""

    return [
        HistoryShowCommand(context),
        HistoryClearCommand(context),
    ]
