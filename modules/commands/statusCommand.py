"""Command-system implementation for `statusCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class StatusCommand(BaseCommand):
    """Implements the `/status` CLI command behavior and response generation."""
    name = "status"
    help_message = "Show Aura runtime health summary."

    def __init__(self, context):
        """Initialize `StatusCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.commandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        context = self.context

        db_connected = False
        database = getattr(context, "database", None)
        if database is not None:
            connection = getattr(database, "connection", None)
            if connection is not None and hasattr(connection, "is_connected"):
                try:
                    db_connected = bool(connection.is_connected())
                except Exception:
                    db_connected = False
            elif connection is not None:
                db_connected = True

        llm_ready = getattr(context, "llm", None) is not None
        modules_count = len(getattr(context, "modules", {}))
        scheduler_running = bool(getattr(getattr(context, "scheduler", None), "running", False))

        return (
            "------ STATUS ------\n"
            f"database_connected: {db_connected}\n"
            f"llm_ready: {llm_ready}\n"
            f"modules_loaded: {modules_count}\n"
            f"scheduler_running: {scheduler_running}"
        )

