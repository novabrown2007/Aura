"""Status command for Aura CLI."""

from __future__ import annotations

from modules.commands.baseCommand import BaseCommand


class StatusCommand(BaseCommand):
    """Report high-level runtime status."""

    path = ("status",)
    description = "Show high-level runtime status."

    def execute(self, args):
        """Return a concise runtime status summary."""

        scheduler = getattr(self.context, "scheduler", None)
        database = getattr(self.context, "database", None)
        modules = sorted(self.context.modules.keys())
        lines = [
            "Aura status:",
            f"modules: {', '.join(modules) if modules else 'none'}",
            f"scheduler_running: {bool(getattr(scheduler, 'running', False))}",
            f"database_connected: {bool(getattr(getattr(database, 'connection', None), 'is_connected', lambda: False)()) if database else False}",
            f"pending_restart: {bool(getattr(self.context, 'restart_requested', False))}",
        ]
        return self.ok("\n".join(lines))
