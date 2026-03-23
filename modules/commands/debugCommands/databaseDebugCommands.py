from modules.commands.baseCommand import BaseCommand


class DatabaseDebugCommand(BaseCommand):
    """
    Debug command for checking database status and connectivity.

    Supported commands:
        /debug database
        /debug database status
        /debug database ping
        /debug database schema
    """

    name = "database"
    help_message = "Inspect database status and connectivity."

    def __init__(self, context):
        super().__init__(context)
        if context.logger:
            self.logger = context.logger.getChild("Commands.Debug.Database")

        context.debugCommandHandler.registerCommand(self)

        if self.logger:
            self.logger.info("Initialized.")

    def execute(self, args: list[str]) -> str:
        database = self.context.require("database")
        action = args[0].lower() if args else "status"

        if action == "status":
            connected = False
            connection = getattr(database, "connection", None)
            if connection is not None and hasattr(connection, "is_connected"):
                try:
                    connected = bool(connection.is_connected())
                except Exception:
                    connected = False
            elif connection is not None:
                connected = True

            if connected:
                return "Database status: connected."
            return "Database status: disconnected."

        if action == "ping":
            try:
                row = database.fetchOne("SELECT 1 AS ok")
                if row and str(row.get("ok")) in {"1", "1.0"}:
                    return "Database ping: ok."
                return "Database ping: unexpected response."
            except Exception as error:
                if self.logger:
                    self.logger.error(f"Database ping failed: {error}")
                return f"Database ping failed: {error}"

        if action == "schema":
            try:
                database_name = getattr(database, "database_name", None)
                if not database_name:
                    return "Database schema: unavailable (database name not provided)."

                rows = database.fetchAll(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = ?
                    ORDER BY table_name
                    """,
                    (database_name,),
                )
                if not rows:
                    return "Database schema: no tables found."

                lines = ["------ DATABASE TABLES ------"]
                for row in rows:
                    lines.append(row["table_name"])
                return "\n".join(lines)
            except Exception as error:
                if self.logger:
                    self.logger.error(f"Database schema query failed: {error}")
                return f"Database schema query failed: {error}"

        return "Usage:\n/debug database\n/debug database status\n/debug database ping\n/debug database schema"
