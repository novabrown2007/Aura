"""Main Tkinter window for the Aura Developer UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from interface.developerUI.rendering import LayoutManager, PanelRenderer


class DeveloperWindow:
    """Main operator console window."""

    def __init__(self, developerUI):
        self.developerUI = developerUI
        self.context = developerUI.context
        self.state = developerUI.state
        self.refreshRate = int(developerUI.refreshRate)
        self.isClosing = False
        logger = getattr(self.context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.Window") if logger else None

        self.root = tk.Tk()
        self.root.title("Aura Developer Console")
        self.root.geometry("1280x820")
        self.root.minsize(980, 640)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.layoutManager = LayoutManager(self.context, parent=self.root)
        self.tabs, self.panels = self.layoutManager.build()
        self.renderer = PanelRenderer(self.panels, self.context)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.header = ttk.Label(self.root, text="Aura Developer Console - realtime operational visibility")
        self.header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.status = ttk.Label(self.root, text="", anchor="w")
        self.status.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))

        self._scheduleRefresh()

    def run(self) -> int:
        """Run the blocking Tkinter event loop."""

        self.root.mainloop()
        return 0

    def refresh(self):
        """Refresh UI panels from runtime state."""

        try:
            self.developerUI.refreshState()
            snapshot = self.state.snapshot()
            self.renderer.refresh(snapshot)
            self.status.configure(
                text=(
                f"Events: {len(snapshot.events)} | Errors: {len(snapshot.errors)} | Uptime: {snapshot.system.get('uptimeSeconds', 0)}s"
                )
            )
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Developer UI refresh failed: {error}")
        finally:
            if not self.isClosing:
                self._scheduleRefresh()

    def _scheduleRefresh(self):
        self.root.after(max(100, self.refreshRate), self.refresh)

    def close(self):
        """Shutdown UI subscriptions before closing."""

        self.isClosing = True
        try:
            self.developerUI.shutdown()
        finally:
            self.root.destroy()
