"""Notifications debug command for Aura CLI."""

from modules.commands.baseCommand import BaseCommand


class NotificationsDebugCommand(BaseCommand):
    """Show notification subsystem diagnostics."""

    path = ("debug", "notifications")
    description = "Show notification subsystem debug information."

    def execute(self, args):
        """Return high-level notification diagnostics."""

        notifications = self.context.require("notifications")
        rows = notifications.listNotifications()
        due_rows = notifications.listDueNotifications()
        unread_count = len(
            [row for row in rows if str(row.get("status") or "").lower() not in {"read", "dismissed"}]
        )
        lines = [
            f"entries: {len(rows)}",
            f"due_now: {len(due_rows)}",
            f"active_unread: {unread_count}",
        ]
        return self.ok("\n".join(lines))
