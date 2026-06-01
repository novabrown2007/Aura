"""Assistant status indicator widgets for Aura's Windows overlay."""

from __future__ import annotations


class AssistantStatusIndicator:
    """Small textual status indicator that can be embedded in the bubble."""

    def __init__(self, parent=None, context=None):
        self.parent = parent
        self.context = context
        self.label = None
        self.state = "IDLE"
        self.message = ""

    def attach(self, parent):
        from tkinter import Label

        self.parent = parent
        self.label = Label(
            parent,
            text="IDLE",
            bg="#172232",
            fg="#f0f6ff",
            font=("Segoe UI Semibold", 8),
            padx=10,
            pady=4,
            relief="flat",
        )
        self.label.pack(side="right", anchor="e", padx=(8, 0))
        self._render()
        return self.label

    def setState(self, state: str, message: str = ""):
        self.state = str(state or "IDLE").upper()
        self.message = str(message or "")
        self._render()

    def _render(self):
        if self.label is None:
            return
        text = self.state
        if self.message:
            text = f"{text} · {self.message}"
        self.label.configure(text=text)
