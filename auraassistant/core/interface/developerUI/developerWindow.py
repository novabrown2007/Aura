"""Main PyQt6 window for the Aura Developer UI."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from auraassistant.core.interface.developerUI.rendering import LayoutManager, PanelRenderer


class DeveloperWindow(QMainWindow):
    """Main operator console window."""

    def __init__(self, developerUI):
        super().__init__()
        self.developerUI = developerUI
        self.context = developerUI.context
        self.state = developerUI.state
        self.refreshRate = int(developerUI.refreshRate)
        self.isClosing = False
        logger = getattr(self.context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Window") if logger else None

        self.setWindowTitle("Aura Developer Console")
        self.resize(1280, 820)
        self.setMinimumSize(980, 640)

        self.layoutManager = LayoutManager(self.context)
        self.tabs, self.panels = self.layoutManager.build()
        self.renderer = PanelRenderer(self.panels, self.context)

        root = QWidget()
        layout = QVBoxLayout()
        self.header = QLabel("Aura Developer Console - realtime operational visibility")
        layout.addWidget(self.header)
        layout.addWidget(self.tabs)
        root.setLayout(layout)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(max(100, self.refreshRate))

    def refresh(self):
        """Refresh UI panels from runtime state."""

        try:
            self.developerUI.refreshState()
            snapshot = self.state.snapshot()
            self.renderer.refresh(snapshot)
            self.statusBar().showMessage(
                f"Events: {len(snapshot.events)} | Errors: {len(snapshot.errors)} | Uptime: {snapshot.system.get('uptimeSeconds', 0)}s"
            )
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Developer UI refresh failed: {error}")

    def closeEvent(self, event):
        """Shutdown UI subscriptions before closing."""

        self.isClosing = True
        try:
            self.developerUI.shutdown()
        finally:
            event.accept()

