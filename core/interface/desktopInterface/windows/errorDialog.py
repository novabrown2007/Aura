"""Windows error dialog helpers for Aura."""

from tkinter import BOTH, Button, Frame, Text, Tk, Toplevel


def showErrorPopup(parent, message: str):
    """
    Display a modal error popup with copy support.
    """

    dialog = Toplevel(parent)
    dialog.title("Aura Error")
    dialog.geometry("520x260")
    dialog.configure(bg="#10161f")
    dialog.transient(parent)
    dialog.grab_set()

    body = Frame(dialog, bg="#10161f")
    body.pack(fill=BOTH, expand=True, padx=16, pady=16)

    text_box = Text(
        body,
        bg="#0b1017",
        fg="#e8eef7",
        insertbackground="#e8eef7",
        relief="flat",
        borderwidth=0,
        wrap="word",
        padx=12,
        pady=12,
    )
    text_box.pack(fill=BOTH, expand=True)
    text_box.insert("1.0", str(message))
    text_box.configure(state="disabled")

    def _copyError():
        dialog.clipboard_clear()
        dialog.clipboard_append(str(message))

    actions = Frame(dialog, bg="#10161f")
    actions.pack(fill="x", padx=16, pady=(0, 16))

    Button(
        actions,
        text="Copy Error",
        command=_copyError,
        bg="#3ea6ff",
        fg="#08111d",
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
    ).pack(side="left")

    Button(
        actions,
        text="Close",
        command=dialog.destroy,
        bg="#1b2533",
        fg="#e8eef7",
        relief="flat",
        bd=0,
        padx=12,
        pady=8,
    ).pack(side="right")

    return dialog


def showStandaloneErrorPopup(message: str):
    """
    Display an error popup when no parent window exists yet.
    """

    root = Tk()
    root.withdraw()
    try:
        dialog = showErrorPopup(root, message)
        dialog.wait_window()
    finally:
        root.destroy()
