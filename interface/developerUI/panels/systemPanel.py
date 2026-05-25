"""System panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class SystemPanel(QWidget):
    """Display subsystem status, modules, uptime, and event throughput."""

    title = "System"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        system = snapshot.system
        modules = system.get("modules", {})
        lines = [
            "[SYSTEM]",
            f"Uptime Seconds: {system.get('uptimeSeconds', 0)}",
            f"Event Count: {system.get('eventCount', 0)}",
            "",
            "Event Listeners:",
            str(system.get("events", {})),
            "",
            "Subsystems:",
            f"Voice: {'Online' if snapshot.voice else 'Unavailable'}",
            f"Memory: {'Online' if snapshot.memory else 'Unavailable'}",
            f"Bridge: {'Connected' if snapshot.bridge.get('connected') else 'Disconnected'}",
            f"Providers: {'Available' if snapshot.providers.get('available') else 'Unavailable'}",
            "",
            "Loaded Modules:",
        ]
        if isinstance(modules, dict):
            for name, module in sorted(modules.items()):
                lines.append(f"- {name}: loaded={module.get('loaded', True)} class={module.get('class')}")
        self.text.setPlainText("\n".join(str(line) for line in lines))

