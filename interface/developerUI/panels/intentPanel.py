"""Intent panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class IntentPanel(QWidget):
    """Display generated intents, confidence, arguments, and status."""

    title = "Intents"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        lines = ["Intent Flow"]
        if not snapshot.intents:
            lines.append("No intent events observed.")
        for item in snapshot.intents[-80:]:
            payload = item.get("payload", {})
            lines.append("")
            lines.append(f"[{item.get('timestamp')}] {item.get('name')}")
            lines.append(f"Intent: {payload.get('intent') or payload.get('name') or payload.get('toolName') or ''}")
            lines.append(f"Confidence: {payload.get('confidence', '')}")
            lines.append(f"Arguments: {payload.get('arguments', {})}")
            lines.append(f"Status: {payload.get('status', payload.get('success', ''))}")
        self.text.setPlainText("\n".join(lines))

