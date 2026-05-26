"""Notification panel for the Aura Developer UI."""

from __future__ import annotations

from interface.developerUI.panels.basePanel import TextPanel


class NotificationPanel(TextPanel):
    """Display assistant notifications and alerts."""

    title = "Notifications"

    def refresh(self, snapshot):
        lines = ["[NOTIFICATIONS]"]
        if not snapshot.notifications:
            lines.append("No notifications observed.")
        for notification in snapshot.notifications[-100:]:
            payload = notification.get("payload", {})
            lines.append("")
            lines.append(f"[{notification.get('timestamp')}] {notification.get('name')}")
            lines.append(f"Priority: {payload.get('priority', '')}")
            lines.append(f"Source: {payload.get('source') or payload.get('source_module') or ''}")
            lines.append(f"Content: {payload.get('content') or payload.get('message') or payload}")
        self.setText("\n".join(str(line) for line in lines))
