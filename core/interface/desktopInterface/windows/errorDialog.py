"""Reusable error dialog helpers for Aura's Windows interface.

This module provides a copy-friendly popup dialog for runtime failures so
users can quickly capture diagnostics without opening logs manually.
"""

from tkinter import BOTH, END, LEFT, RIGHT, WORD, Button, Text, Toplevel, Tk

POPUP_BG = "#10161f"
TEXT_BG = "#0c1118"
TEXT_PRIMARY = "#ebf2fb"
TEXT_MUTED = "#9aa8bc"
ACCENT = "#3ea6ff"
ACCENT_ACTIVE = "#68bcff"
BUTTON_BG = "#1a2330"


def showErrorPopup(parent, message: str, title: str = "Aura Error"):
    """Display a modal error popup with copy-to-clipboard support.

    Args:
        parent:
            Parent Tk widget used as dialog owner.
        message (str):
            Error text shown in the dialog body.
        title (str):
            Window title for the dialog.
    """

    dialog = Toplevel(parent)
    dialog.title(title)
    dialog.geometry("680x320")
    dialog.minsize(520, 260)
    dialog.configure(bg=POPUP_BG)
    dialog.transient(parent)
    dialog.grab_set()

    text = Text(
        dialog,
        wrap=WORD,
        bg=TEXT_BG,
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        borderwidth=0,
        padx=14,
        pady=14,
        font=("Consolas", 10),
        selectbackground=ACCENT,
        selectforeground="#08111d",
    )
    text.pack(fill=BOTH, expand=True, padx=10, pady=(10, 6))
    text.insert(END, str(message))
    text.configure(state="disabled")

    def _copyError():
        """Copy the full error message to the OS clipboard."""

        dialog.clipboard_clear()
        dialog.clipboard_append(str(message))
        dialog.update_idletasks()

    copy_button = Button(
        dialog,
        text="Copy Error",
        command=_copyError,
        bg=ACCENT,
        fg="#08111d",
        activebackground=ACCENT_ACTIVE,
        activeforeground="#08111d",
        relief="flat",
        bd=0,
        padx=14,
        pady=8,
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
    )
    copy_button.pack(side=LEFT, padx=(10, 6), pady=(0, 10))

    close_button = Button(
        dialog,
        text="Close",
        command=dialog.destroy,
        bg=BUTTON_BG,
        fg=TEXT_MUTED,
        activebackground="#263244",
        activeforeground=TEXT_PRIMARY,
        relief="flat",
        bd=0,
        padx=14,
        pady=8,
        font=("Segoe UI", 10),
        cursor="hand2",
    )
    close_button.pack(side=RIGHT, padx=(6, 10), pady=(0, 10))


def showStandaloneErrorPopup(message: str, title: str = "Aura Error"):
    """Show an error popup when no main app window exists yet.

    Args:
        message (str):
            Error text shown in the dialog body.
        title (str):
            Window title for the dialog.
    """

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    showErrorPopup(root, message, title=title)
    root.wait_window(root.winfo_children()[-1])
    root.destroy()
