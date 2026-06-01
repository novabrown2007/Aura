"""Toast-style desktop popup notifications for Aura."""

from __future__ import annotations

from interface.desktop.windows.models import OverlayNotification


class NotificationPopup:
    """A single transient notification popup."""

    def __init__(self, context=None, root=None, notification: OverlayNotification | None = None, onDismiss=None):
        self.context = context
        self.root = root
        self.notification = notification or OverlayNotification()
        self.onDismiss = onDismiss
        self.window = None
        self.visible = False

    def show(self):
        if self.window is not None:
            return self.window
        from tkinter import BOTH, Frame, Label, Toplevel, Button

        master = self.root
        if master is None:
            return None
        window = Toplevel(master)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.configure(bg="#111722")

        title = self.notification.title or "Aura"
        window.title(title)

        card = Frame(window, bg="#111722", highlightbackground="#243042", highlightthickness=1, bd=0)
        card.pack(fill=BOTH, expand=True)
        Label(card, text=title, bg="#111722", fg="#e8eef7", font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=12, pady=(10, 4))
        Label(card, text=self.notification.message, bg="#111722", fg="#93a1b5", font=("Segoe UI", 9), wraplength=280, justify="left").pack(anchor="w", padx=12, pady=(0, 8))
        Button(card, text="Dismiss", command=self.dismiss, bg="#1b2533", fg="#e8eef7", relief="flat", bd=0, padx=10, pady=4).pack(anchor="e", padx=12, pady=(0, 12))

        self.window = window
        self.visible = True
        self._scheduleDismiss()
        return window

    def dismiss(self):
        if self.window is None:
            return
        try:
            self.window.destroy()
        except Exception:
            pass
        self.window = None
        self.visible = False
        if callable(self.onDismiss):
            try:
                self.onDismiss(self)
            except Exception:
                pass

    def _scheduleDismiss(self):
        if self.window is None:
            return
        duration = self._durationForPriority(self.notification.priority)
        if duration <= 0:
            return
        try:
            self.window.after(duration, self.dismiss)
        except Exception:
            pass

    @staticmethod
    def _durationForPriority(priority: str) -> int:
        mapping = {
            "LOW": 3500,
            "NORMAL": 5000,
            "HIGH": 8000,
            "CRITICAL": 0,
            "EMERGENCY": 0,
        }
        return mapping.get(str(priority or "NORMAL").upper(), 5000)
