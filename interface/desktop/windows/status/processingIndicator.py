"""Processing indicator for Aura's Windows overlay."""

from __future__ import annotations


class ProcessingIndicator:
    """Simple status label for work-in-progress activity."""

    def __init__(self, parent=None, context=None):
        self.parent = parent
        self.context = context
        self.label = None
        self.active = False

    def attach(self, parent):
        from tkinter import Label

        self.parent = parent
        self.label = Label(parent, text="", bg="#111b27", fg="#5ab0ff", font=("Segoe UI", 8))
        self.label.pack(anchor="w", pady=(0, 3))
        self._render()
        return self.label

    def setActive(self, active: bool, message: str = "Processing"):
        self.active = bool(active)
        self.message = str(message or "Processing")
        self._render()

    def _render(self):
        if self.label is None:
            return
        self.label.configure(text=self.message if self.active else "")
