"""Shared Tkinter panel primitives for the Aura Developer UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class TextPanel(ttk.Frame):
    """Base panel with a read-only text area."""

    title = "Panel"

    def __init__(self, parent):
        super().__init__(parent)
        self.text = tk.Text(self, wrap="word", height=24)
        self.text.configure(state="disabled")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def setText(self, content: str):
        """Replace text content without allowing user edits."""

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", str(content))
        self.text.configure(state="disabled")
