"""Minimal blank window used as the first UI surface for Aura."""

from __future__ import annotations


class BlankWindowApp:
    """Create and run a plain empty desktop window."""

    def __init__(self, title: str = "Aura", width: int = 960, height: int = 640):
        self.title = str(title or "Aura")
        self.width = int(width or 960)
        self.height = int(height or 640)
        self.root = None

    def build(self):
        """Create the Tk root window without starting the event loop."""

        try:
            import tkinter as tk
        except Exception as error:
            raise RuntimeError("Tkinter is required to open the blank Aura window.") from error

        root = tk.Tk()
        root.title(self.title)
        root.geometry(f"{self.width}x{self.height}")
        root.minsize(480, 320)
        root.configure(bg="#111111")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.root = root
        return root

    def run(self):
        """Show the blank window and block until it closes."""

        root = self.root or self.build()
        root.mainloop()

    def close(self):
        """Destroy the window if it exists."""

        root = self.root
        if root is None:
            return
        try:
            root.destroy()
        finally:
            self.root = None
