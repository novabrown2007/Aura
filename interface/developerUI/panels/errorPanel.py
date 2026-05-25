"""Error panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class ErrorPanel(QWidget):
    """Display recent exceptions and operational failures."""

    title = "Errors"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        lines = ["[ERRORS]"]
        if not snapshot.errors:
            lines.append("No errors observed.")
        for error in snapshot.errors[-100:]:
            lines.append("")
            lines.append(f"[{error.get('timestamp')}] {error.get('name')}")
            lines.append(f"Error: {error.get('error')}")
            lines.append(f"Payload: {error.get('payload')}")
        self.text.setPlainText("\n".join(str(line) for line in lines))

