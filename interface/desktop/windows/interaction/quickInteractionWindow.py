"""Compact quick-interaction window for Aura on Windows."""

from __future__ import annotations

from interface.desktop.windows.interaction.compactConversationView import CompactConversationView
from interface.desktop.windows.interaction.overlayInputHandler import OverlayInputHandler


class QuickInteractionWindow:
    """Lightweight prompt-and-reply surface for short assistant interactions."""

    def __init__(self, context=None, root=None, overlayManager=None):
        self.context = context
        self.root = root
        self.overlayManager = overlayManager
        self.window = None
        self.visible = False
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Desktop.QuickInteraction") if logger else None
        self.conversationView = CompactConversationView(context=context)
        self.inputHandler = OverlayInputHandler(context, overlayManager)
        self.submitCallback = None

    def ensureWindow(self):
        if self.window is not None:
            return self.window
        from tkinter import BOTH, Button, Entry, Frame, Label, Toplevel

        if self.root is None or not hasattr(self.root, "tk"):
            return None
        window = Toplevel(self.root)
        window.title("Aura")
        window.geometry("420x280")
        window.attributes("-topmost", True)
        window.configure(bg="#111722")
        window.withdraw()

        header = Frame(window, bg="#111722")
        header.pack(fill="x", padx=12, pady=(12, 6))
        Label(header, text="Quick Aura", bg="#111722", fg="#e8eef7", font=("Segoe UI Semibold", 10)).pack(side="left")

        self.viewFrame = Frame(window, bg="#111722")
        self.viewFrame.pack(fill=BOTH, expand=True, padx=12, pady=(0, 8))
        self.conversationView.attach(self.viewFrame)

        inputRow = Frame(window, bg="#111722")
        inputRow.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = Entry(inputRow, bg="#171f2b", fg="#e8eef7", insertbackground="#e8eef7", relief="flat", bd=0)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.inputHandler.bindEntry(self.entry)
        Button(inputRow, text="Send", command=self.submit, bg="#3ea6ff", fg="#08111d", relief="flat", bd=0, padx=10, pady=5).pack(side="right", padx=(8, 0))

        window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window = window
        return window

    def setSubmitCallback(self, callback):
        self.submitCallback = callback

    def show(self):
        window = self.ensureWindow()
        if window is None:
            return
        try:
            window.deiconify()
            window.lift()
            window.focus_force()
            self.visible = True
            if hasattr(self, "entry"):
                self.entry.focus_set()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Quick interaction show failed: {error}")

    def hide(self):
        if self.window is None:
            return
        try:
            self.window.withdraw()
            self.visible = False
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Quick interaction hide failed: {error}")

    def submit(self):
        text = ""
        if hasattr(self, "entry"):
            try:
                text = self.entry.get().strip()
                self.entry.delete(0, "end")
            except Exception:
                text = ""
        if not text:
            return
        self.conversationView.append("You", text)
        if callable(self.submitCallback):
            try:
                self.submitCallback(text)
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Quick interaction submit failed: {error}")

    def appendReply(self, speaker: str, text: str):
        self.conversationView.append(speaker, text)

    def _getConfigValue(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        value = config.get(key, None)
        if value is None and "." not in key:
            value = config.get(f"interface.desktop.windows.{key}", None)
        if value is None:
            return default
        return value
