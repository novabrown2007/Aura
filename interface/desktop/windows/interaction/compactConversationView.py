"""Compact conversation display for Aura's Windows overlay."""

from __future__ import annotations


class CompactConversationView:
    """Minimal scrollable conversation surface."""

    def __init__(self, parent=None, context=None):
        self.parent = parent
        self.context = context
        self.widget = None
        self.lines = []

    def attach(self, parent):
        from tkinter import BOTH, END, Frame, Text

        self.parent = parent
        container = Frame(parent, bg="#0f141c", highlightbackground="#243042", highlightthickness=1, bd=0)
        container.pack(fill=BOTH, expand=True)
        self.widget = Text(container, height=7, wrap="word", bg="#0f141c", fg="#e8eef7", insertbackground="#e8eef7", relief="flat", borderwidth=0)
        self.widget.pack(fill=BOTH, expand=True, padx=1, pady=1)
        self.widget.insert(END, "")
        self.widget.configure(state="disabled")
        return self.widget

    def append(self, speaker: str, text: str):
        self.lines.append((str(speaker or ""), str(text or "")))
        if self.widget is None:
            return
        from tkinter import END

        self.widget.configure(state="normal")
        self.widget.insert(END, f"{speaker}: {text}\n")
        self.widget.see(END)
        self.widget.configure(state="disabled")

