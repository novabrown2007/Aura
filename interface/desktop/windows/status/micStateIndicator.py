"""Microphone state indicator for Aura's Windows overlay."""

from __future__ import annotations


class MicStateIndicator:
    """Track wake word, VAD, mute, and recording state."""

    def __init__(self, parent=None, context=None):
        self.parent = parent
        self.context = context
        self.label = None
        self.state = "IDLE"
        self.muted = False
        self.activity = False
        self.confidence = 0.0
        self.silence = 0.0

    def attach(self, parent):
        from tkinter import Label

        self.parent = parent
        self.label = Label(parent, text="Mic · idle", bg="#111b27", fg="#96a4b6", font=("Segoe UI", 8))
        self.label.pack(anchor="w", pady=(0, 3))
        self._render()
        return self.label

    def setState(self, state: str, activity: bool = False, muted: bool = False, confidence: float = 0.0, silence: float = 0.0):
        self.state = str(state or "IDLE").upper()
        self.activity = bool(activity)
        self.muted = bool(muted)
        self.confidence = float(confidence or 0.0)
        self.silence = float(silence or 0.0)
        self._render()

    def _render(self):
        if self.label is None:
            return
        suffix = " muted" if self.muted else ""
        if self.state == "LISTENING":
            text = f"Mic · listening {self.confidence:.2f}{suffix}"
        elif self.state == "PROCESSING":
            text = f"Mic · processing{suffix}"
        elif self.state == "RESPONDING":
            text = f"Mic · responding{suffix}"
        else:
            text = f"Mic · {self.state.lower()}{suffix}"
        self.label.configure(text=text)
