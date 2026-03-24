"""Logs debug command for Aura CLI."""

from pathlib import Path

from modules.commands.baseCommand import BaseCommand


class LogsDebugCommand(BaseCommand):
    """Show recent log lines from the current log file."""

    path = ("debug", "logs")
    description = "Show recent log lines. Usage: /debug logs [line_count]"

    def execute(self, args):
        """Return the tail of the current run log file."""

        line_count = int(args[0]) if args else 20
        log_path = Path(self.context.logger.logFilePath)
        if not log_path.exists():
            return self.fail("Current log file does not exist.")
        with open(log_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        return self.ok("".join(lines[-line_count:]).rstrip() or "(log file is empty)")

