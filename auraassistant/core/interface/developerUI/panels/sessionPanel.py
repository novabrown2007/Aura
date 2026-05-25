"""Session panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class SessionPanel(QWidget):
    """Display active sessions and conversation context."""

    title = "Sessions"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        lines = ["Active Sessions"]
        if not snapshot.sessions:
            lines.append("No active sessions.")
        for session in snapshot.sessions:
            lines.append("")
            lines.append(f"Session: {session.get('sessionId')}")
            lines.append(f"Interface: {session.get('interface', '')}")
            lines.append(f"Started: {session.get('startedAt', '')}")
            lines.append(f"Context: {session.get('context', {})}")
        self.text.setPlainText("\n".join(lines))

