"""Memory panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class MemoryPanel(QWidget):
    """Display retrieval scores, injected memories, and memory summaries."""

    title = "Memory"

    def __init__(self):
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def refresh(self, snapshot):
        memory = snapshot.memory
        lines = [
            "[MEMORY]",
            f"Retrieved: {memory.get('retrieved', 0)}",
            f"Injected: {memory.get('injected', 0)}",
            f"Filtered: {memory.get('filtered', 0)}",
            f"Top Score: {memory.get('topScore', 0.0)}",
            "",
            "Debug Output:",
            memory.get("debugOutput", "") or "No memory retrieval debug output yet.",
        ]
        self.text.setPlainText("\n".join(str(line) for line in lines))

