"""Notification panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class NotificationPanel(QWidget):
    """Display assistant notifications and alerts."""

    title = "Notifications"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

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
        self.text.setPlainText("\n".join(str(line) for line in lines))

