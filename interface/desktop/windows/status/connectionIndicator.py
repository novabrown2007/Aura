"""Connection indicator for Aura's Windows overlay."""

from __future__ import annotations


class ConnectionIndicator:
    """Display provider connectivity in the desktop bubble."""

    def __init__(self, parent=None, context=None):
        self.parent = parent
        self.context = context
        self.label = None
        self.connected = True
        self.provider = ""

    def attach(self, parent):
        from tkinter import Label

        self.parent = parent
        self.label = Label(parent, text="Provider · connected", bg="#111b27", fg="#96a4b6", font=("Segoe UI", 8))
        self.label.pack(anchor="w", pady=(0, 3))
        self._render()
        return self.label

    def setState(self, connected: bool, provider: str = ""):
        self.connected = bool(connected)
        self.provider = str(provider or "")
        self._render()

    def _render(self):
        if self.label is None:
            return
        state = "connected" if self.connected else "disconnected"
        suffix = f" ({self.provider})" if self.provider else ""
        self.label.configure(text=f"Provider · {state}{suffix}")
