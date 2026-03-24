"""Database debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class DatabaseDebugCommand(BaseCommand):
    """Show database connection details."""

    path = ("debug", "database")
    description = "Show database debug information."

    def execute(self, args):
        """Return basic database diagnostics."""

        database = self.context.require("database")
        connected = bool(getattr(getattr(database, "connection", None), "is_connected", lambda: False)())
        lines = [
            f"type: {database.__class__.__name__}",
            f"database_name: {getattr(database, 'database_name', None)}",
            f"connected: {connected}",
        ]
        return self.ok("\n".join(lines))

