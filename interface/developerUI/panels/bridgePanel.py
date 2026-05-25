"""Bridge panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class BridgePanel(QWidget):
    """Display bridge connection state and recent protocol traffic."""

    title = "Bridge"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        bridge = snapshot.bridge
        lines = ["[BRIDGE]", f"Connected: {bridge.get('connected', False)}"]
        if bridge.get("bridgeName"):
            lines.append(f"Bridge: {bridge.get('bridgeName')}")
        lines.append("")
        lines.append("Subscriptions:")
        lines.append(str(bridge.get("subscriptions", [])))
        lines.append("")
        lines.append("Recent Messages:")
        for message in (bridge.get("messages") or [])[-60:]:
            lines.append(f"- {message.get('timestamp')} {message.get('name')}: {message.get('summary')}")
        self.text.setPlainText("\n".join(str(line) for line in lines))

