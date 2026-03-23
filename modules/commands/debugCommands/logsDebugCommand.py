"""Command-system implementation for `logsDebugCommand` within Aura's CLI architecture."""

from modules.commands.baseCommand import BaseCommand


class LogsDebugCommand(BaseCommand):
    """
    Implements the `/logs-debug` CLI command behavior and response generation.
    """

    name = "logs"
    help_message = "Inspect or clear persisted command logs."

    def __init__(self, context):
        """Initialize `LogsDebugCommand` with required dependencies and internal state."""
        super().__init__(context)
        context.debugCommandHandler.registerCommand(self)

    def execute(self, args: list[str]) -> str:
        """Execute the command using parsed arguments and return a user-facing message."""
        if not args:
            return self._usage()

        action = args[0].lower()
        database = self.context.require("database")

        if action == "tail":
            limit = self._parseLimit(args, 1, default=20)
            if limit is None:
                return "Usage: /debug logs tail [limit]"
            rows = database.fetchAll(
                """
                SELECT command_text, command_root, status, response_text, error_text, duration_ms, executed_at
                FROM command_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return self._formatRows(rows, title=f"------ COMMAND LOGS (tail {limit}) ------")

        if action == "search":
            if len(args) < 2:
                return "Usage: /debug logs search <term> [limit]"
            term = args[1]
            limit = self._parseLimit(args, 2, default=20)
            if limit is None:
                return "Usage: /debug logs search <term> [limit]"
            like = f"%{term}%"
            rows = database.fetchAll(
                """
                SELECT command_text, command_root, status, response_text, error_text, duration_ms, executed_at
                FROM command_logs
                WHERE command_text LIKE ?
                   OR response_text LIKE ?
                   OR error_text LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (like, like, like, limit),
            )
            return self._formatRows(rows, title=f'------ COMMAND LOGS SEARCH "{term}" ------')

        if action == "errors":
            limit = self._parseLimit(args, 1, default=20)
            if limit is None:
                return "Usage: /debug logs errors [limit]"
            rows = database.fetchAll(
                """
                SELECT command_text, command_root, status, response_text, error_text, duration_ms, executed_at
                FROM command_logs
                WHERE status IN ('error', 'invalid')
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return self._formatRows(rows, title=f"------ COMMAND LOG ERRORS (last {limit}) ------")

        if action == "clear":
            database.execute("DELETE FROM command_logs")
            return "Command logs cleared."

        return self._usage()

    @staticmethod
    def _parseLimit(args: list[str], index: int, default: int) -> int:
        """Implement `_parseLimit` as part of this component's public/internal behavior."""
        if len(args) <= index:
            return default
        try:
            return max(1, int(args[index]))
        except ValueError:
            return None

    @staticmethod
    def _formatRows(rows, title: str) -> str:
        """Implement `_formatRows` as part of this component's public/internal behavior."""
        if not rows:
            return "No command logs found."

        lines = [title]
        for row in rows:
            command_text = row.get("command_text", "")
            status = row.get("status", "")
            duration_ms = row.get("duration_ms", "")
            lines.append(f"{status} | {duration_ms}ms | {command_text}")
        return "\n".join(lines)

    @staticmethod
    def _usage() -> str:
        """Implement `_usage` as part of this component's public/internal behavior."""
        return (
            "Usage:\n"
            "/debug logs tail [limit]\n"
            "/debug logs search <term> [limit]\n"
            "/debug logs errors [limit]\n"
            "/debug logs clear"
        )

