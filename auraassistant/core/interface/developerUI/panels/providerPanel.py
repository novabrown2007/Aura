"""Provider panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class ProviderPanel(QWidget):
    """Display LLM provider state, fallback state, and timing."""

    title = "Providers"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        providers = snapshot.providers
        lines = ["[PROVIDER]", f"Offline Mode: {providers.get('offlineMode', '')}"]
        for name, provider in (providers.get("providers") or {}).items():
            lines.append("")
            lines.append(f"Provider: {name}")
            lines.append(f"Initialized: {provider.get('initialized')}")
            lines.append(f"Active: {provider.get('active')}")
            lines.append(f"Fallback: {provider.get('fallback')}")
        lines.append("")
        lines.append(f"Performance: {snapshot.performance.get('aggregates', {})}")
        self.text.setPlainText("\n".join(str(line) for line in lines))

