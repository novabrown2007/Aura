"""Event panel for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class EventPanel(QWidget):
    """Display recent Aura events."""

    title = "Events"

    def __init__(self):
        super().__init__()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Time", "Category", "Event", "Source", "Payload"])
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

    def refresh(self, snapshot):
        events = snapshot.events[-200:]
        self.table.setRowCount(len(events))
        for row, event in enumerate(events):
            values = [
                event.get("timestamp", ""),
                event.get("category", ""),
                event.get("name", ""),
                event.get("source", ""),
                event.get("summary", ""),
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

