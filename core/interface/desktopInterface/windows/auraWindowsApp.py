"""Tkinter-based Windows desktop application for Aura.

This module defines the primary GUI class used by the Windows interface
branch. It provides:
- A conversation transcript panel
- A text input box for prompts/commands
- A send button with busy-state handling
- Background processing so the UI remains responsive
"""

from __future__ import annotations

from queue import Empty, Queue
from threading import Thread
from tkinter import (
    END,
    DISABLED,
    NORMAL,
    BOTH,
    LEFT,
    RIGHT,
    X,
    Y,
    Tk,
    Button,
    Frame,
    Label,
    TclError,
    Entry,
)
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

from core.interface.desktopInterface.windows.errorDialog import showErrorPopup

WINDOW_BG = "#0b0f14"
PANEL_BG = "#121821"
TRANSCRIPT_BG = "#0f141c"
INPUT_BG = "#171f2b"
TEXT_PRIMARY = "#e8eef7"
TEXT_MUTED = "#93a1b5"
ACCENT = "#3ea6ff"
ACCENT_ACTIVE = "#68bcff"
BORDER = "#243042"
USER_TEXT = "#f6d37a"
ERROR_TEXT = "#ff8f8f"


class AuraWindowsApp:
    """Windows desktop GUI for sending input to Aura and viewing responses.

    The app delegates processing to Aura's existing `InputManager`, which
    means commands and normal prompts behave exactly like CLI behavior.
    """

    def __init__(self, context):
        """Initialize the Windows app and build user interface widgets.

        Args:
            context (RuntimeContext):
                Initialized runtime context with required managers loaded.
        """

        self.context = context
        self.logger = context.logger.getChild("WindowsApp") if context.logger else None
        self.pendingResponses: Queue[tuple[str, str]] = Queue()
        self.isBusy = False
        self.isClosing = False

        self.root = Tk()
        self.root.title("Aura Assistant")
        self.root.geometry("900x620")
        self.root.minsize(760, 500)
        self.root.configure(bg=WINDOW_BG)
        self.root.protocol("WM_DELETE_WINDOW", self._onWindowClose)

        self._buildLayout()
        self._appendTranscript("Aura", "Windows interface initialized.")
        for warning in getattr(self.context, "bootstrapWarnings", []):
            self._appendTranscript("Aura", f"Startup warning: {warning}")

        if self.logger:
            self.logger.info("AuraWindowsApp initialized.")

    def _buildLayout(self):
        """Create and arrange all Tkinter widgets for the chat interface."""

        header = Frame(self.root, bg=WINDOW_BG)
        header.pack(fill=X, padx=18, pady=(18, 10))

        title_label = Label(
            header,
            text="Aura",
            bg=WINDOW_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 18),
        )
        title_label.pack(side=LEFT)

        subtitle_label = Label(
            header,
            text="Windows desktop interface",
            bg=WINDOW_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        subtitle_label.pack(side=RIGHT, pady=(6, 0))

        transcript_container = Frame(
            self.root,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        transcript_container.pack(fill=BOTH, expand=True, padx=18, pady=(0, 10))

        self.transcript = ScrolledText(
            transcript_container,
            wrap="word",
            state=DISABLED,
            bg=TRANSCRIPT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            borderwidth=0,
            padx=18,
            pady=16,
            font=("Consolas", 11),
            selectbackground=ACCENT,
            selectforeground="#08111d",
        )
        self.transcript.pack(fill=BOTH, expand=True, padx=1, pady=1)

        input_container = Frame(
            self.root,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        input_container.pack(fill=X, padx=18, pady=(0, 18))

        input_inner = Frame(input_container, bg=PANEL_BG)
        input_inner.pack(fill=X, padx=14, pady=14)

        self.inputEntry = Entry(
            input_inner,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.inputEntry.pack(side=LEFT, fill=X, expand=True, ipady=10)
        self.inputEntry.bind("<Return>", self._onSubmitFromKeyboard)

        self.sendButton = Button(
            input_inner,
            text="Send",
            command=self._onSubmit,
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            activeforeground="#08111d",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=18,
            pady=10,
            cursor="hand2",
        )
        self.sendButton.pack(side=RIGHT, padx=(12, 0))

    def run(self):
        """Start the Windows UI event loop."""

        self.inputEntry.focus_set()
        self.root.after(50, self._pollPendingResponses)
        self.root.mainloop()

    def _onSubmitFromKeyboard(self, _event):
        """Handle Enter key submission from the input field."""

        self._onSubmit()

    def _onSubmit(self):
        """Validate input, render user message, and dispatch processing thread."""

        if self.isBusy:
            return

        user_input = self.inputEntry.get().strip()
        if not user_input:
            return

        self.inputEntry.delete(0, END)
        self._appendTranscript("You", user_input)
        self._setBusyState(True)

        worker = Thread(target=self._processInputInWorker, args=(user_input,), daemon=True)
        worker.start()

    def _processInputInWorker(self, user_input: str):
        """Process a single input value in a background thread.

        Args:
            user_input (str):
                The user-provided prompt or command string.
        """

        try:
            input_manager = self.context.require("inputManager")
            response = input_manager.process(user_input)
            self.pendingResponses.put(("response", str(response)))
        except Exception as error:  # pragma: no cover - UI safety path
            if self.logger:
                self.logger.error(f"Input processing failed: {error}")
            self.pendingResponses.put(("error", str(error)))

    def _pollPendingResponses(self):
        """Flush worker results into the transcript and update interface state."""

        if self.isClosing:
            return

        try:
            while True:
                result_type, payload = self.pendingResponses.get_nowait()
                if result_type == "response":
                    self._appendTranscript("Aura", payload)
                    self._setBusyState(False)
                    self._checkForShutdownSignal()
                else:
                    self._appendTranscript("Aura", f"Error: {payload}")
                    self._showErrorPopup(payload)
                    self._setBusyState(False)
        except Empty:
            pass
        finally:
            try:
                if not self.isClosing:
                    self.root.after(50, self._pollPendingResponses)
            except TclError:
                # The root window has already been destroyed.
                return

    def _appendTranscript(self, speaker: str, message: str):
        """Append a message to the transcript panel.

        Args:
            speaker (str):
                Message source label.
            message (str):
                Display text to append.
        """

        speaker_color = TEXT_PRIMARY
        if speaker == "You":
            speaker_color = USER_TEXT
        elif speaker == "Aura" and str(message).startswith("Error:"):
            speaker_color = ERROR_TEXT

        self.transcript.configure(state=NORMAL)
        self.transcript.insert(END, f"{speaker}: ", speaker.lower())
        self.transcript.insert(END, f"{message}\n\n")
        self.transcript.tag_configure("you", foreground=USER_TEXT, font=("Segoe UI Semibold", 10))
        self.transcript.tag_configure("aura", foreground=speaker_color, font=("Segoe UI Semibold", 10))
        self.transcript.configure(state=DISABLED)
        self.transcript.see(END)

    def _setBusyState(self, is_busy: bool):
        """Toggle input controls while a request is in-flight.

        Args:
            is_busy (bool):
                `True` while processing user input, otherwise `False`.
        """

        self.isBusy = is_busy

        if is_busy:
            self.sendButton.configure(
                state=DISABLED,
                text="Thinking...",
                bg="#2b3b4f",
                fg=TEXT_MUTED,
                cursor="arrow",
            )
            self.inputEntry.configure(state=DISABLED, disabledbackground=INPUT_BG, disabledforeground=TEXT_MUTED)
        else:
            self.sendButton.configure(
                state=NORMAL,
                text="Send",
                bg=ACCENT,
                fg="#08111d",
                cursor="hand2",
            )
            self.inputEntry.configure(state=NORMAL, bg=INPUT_BG, fg=TEXT_PRIMARY)
            self.inputEntry.focus_set()

    def _checkForShutdownSignal(self):
        """Close the UI when command handlers request runtime shutdown."""

        if getattr(self.context, "should_exit", False):
            self.root.after(150, self._closeWindow)

    def _onWindowClose(self):
        """Handle user-initiated window close action."""

        if self.isBusy:
            should_close = messagebox.askyesno(
                "Close Aura",
                "Aura is still processing a request. Close anyway?",
            )
            if not should_close:
                return

        self._closeWindow()

    def _closeWindow(self):
        """Destroy the root window safely."""

        if self.isClosing:
            return
        self.isClosing = True

        if self.logger:
            self.logger.info("Closing Windows app.")

        if self.root.winfo_exists():
            self.root.destroy()

    def _showErrorPopup(self, message: str):
        """Render a copy-friendly error dialog for runtime failures.

        Args:
            message (str):
                Error text to display in the popup.
        """

        if self.isClosing:
            return

        try:
            showErrorPopup(self.root, str(message))
        except Exception as error:
            # Fallback to transcript/log only if popup rendering fails.
            if self.logger:
                self.logger.error(f"Error popup failed: {error}")
