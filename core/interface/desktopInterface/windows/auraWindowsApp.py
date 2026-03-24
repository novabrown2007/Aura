"""Tkinter-based Windows desktop shell for Aura."""

from __future__ import annotations

from queue import Empty, Queue
from threading import Thread
from tkinter import BOTH, DISABLED, END, LEFT, NORMAL, TOP, X, Button, Entry, Frame, Label, TclError, Tk
from tkinter.scrolledtext import ScrolledText

from core.interface.desktopInterface.windows.errorDialog import showErrorPopup

WINDOW_BG = "#0b0f14"
PANEL_BG = "#121821"
TRANSCRIPT_BG = "#0f141c"
INPUT_BG = "#171f2b"
SIDEBAR_BG = "#0d1219"
TEXT_PRIMARY = "#e8eef7"
TEXT_MUTED = "#93a1b5"
ACCENT = "#3ea6ff"
ACCENT_ACTIVE = "#68bcff"
BORDER = "#243042"
NAV_INACTIVE = "#192230"
NAV_INACTIVE_ACTIVE = "#233244"


class AuraWindowsApp:
    """
    Minimal Windows desktop shell for Aura's headless runtime.
    """

    def __init__(self, context):
        """Initialize the Windows UI and build the widget tree."""

        self.context = context
        self.logger = context.logger.getChild("WindowsApp") if context.logger else None
        self.pendingResponses: Queue[tuple[str, object]] = Queue()
        self.isBusy = False
        self.isClosing = False
        self.sidebarVisible = False
        self.activePage = "chat"

        self.root = Tk()
        self.root.title("Aura")
        self.root.geometry("900x620")
        self.root.minsize(760, 500)
        self.root.configure(bg=WINDOW_BG)
        self.root.protocol("WM_DELETE_WINDOW", self._closeWindow)

        self._buildLayout()
        self._appendTranscript("Aura", "Windows interface initialized.")

        if self.logger:
            self.logger.info("AuraWindowsApp initialized.")

    def _buildLayout(self):
        """Build the main window layout and page containers."""

        self.shell = Frame(self.root, bg=WINDOW_BG)
        self.shell.pack(fill=BOTH, expand=True)

        self.contentFrame = Frame(self.shell, bg=WINDOW_BG)
        self.contentFrame.pack(side=LEFT, fill=BOTH, expand=True, pady=18, padx=18)

        self.sidebar = Frame(
            self.shell,
            bg=SIDEBAR_BG,
            width=92,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        self.sidebar.pack_propagate(False)

        Label(
            self.sidebar,
            text="A",
            bg=SIDEBAR_BG,
            fg=ACCENT,
            font=("Segoe UI Semibold", 22),
        ).pack(pady=(18, 26))

        self.chatNavButton = self._createSidebarButton("...", "Chat", self._showChatPage)
        self.chatNavButton.pack(side=TOP, fill=X, padx=12, pady=(0, 10))

        self.remindersNavButton = self._createSidebarButton("R", "Reminders", self._showRemindersPage)
        self.remindersNavButton.pack(side=TOP, fill=X, padx=12, pady=(0, 10))

        self.calendarNavButton = self._createSidebarButton("[]", "Calendar", self._showCalendarPage)
        self.calendarNavButton.pack(side=TOP, fill=X, padx=12, pady=(0, 10))

        header = Frame(self.contentFrame, bg=WINDOW_BG)
        header.pack(fill=X, pady=(0, 10))

        self.menuButton = Button(
            header,
            text="≡",
            command=self._toggleSidebar,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=12,
            pady=8,
            cursor="hand2",
        )
        self.menuButton.pack(side=LEFT, padx=(0, 10))

        Label(
            header,
            text="Aura",
            bg=WINDOW_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 18),
        ).pack(side=LEFT)

        self.pageContainer = Frame(self.contentFrame, bg=WINDOW_BG)
        self.pageContainer.pack(fill=BOTH, expand=True)

        self.chatPage = Frame(self.pageContainer, bg=WINDOW_BG)
        self.remindersPage = Frame(self.pageContainer, bg=WINDOW_BG)
        self.calendarPage = Frame(self.pageContainer, bg=WINDOW_BG)

        self._buildChatPage()
        self._buildPlaceholderPage(
            self.remindersPage,
            "Reminders",
            "This branch does not implement reminders UI yet.",
        )
        self._buildPlaceholderPage(
            self.calendarPage,
            "Calendar",
            "This branch does not implement calendar UI yet.",
        )
        self._showPage("chat")

    def _buildChatPage(self):
        """Build the primary chat page widgets."""

        transcript_container = Frame(
            self.chatPage,
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
        )
        self.transcript.pack(fill=BOTH, expand=True, padx=1, pady=1)

        input_container = Frame(
            self.chatPage,
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
        self.sendButton.pack(side=LEFT, padx=(12, 0))

    def _buildPlaceholderPage(self, page, title: str, message: str):
        """Build a placeholder page for not-yet-implemented sections."""

        container = Frame(
            page,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        container.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        Label(
            container,
            text=title,
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14),
        ).pack(pady=(30, 12))

        Label(
            container,
            text=message,
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
        ).pack()

    def _createSidebarButton(self, icon: str, label: str, command):
        """Create a styled sidebar button."""

        return Button(
            self.sidebar,
            text=f"{icon}\n{label}",
            command=command,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=8,
            pady=12,
            cursor="hand2",
            justify="center",
        )

    def _toggleSidebar(self):
        """Show or hide the sidebar drawer."""

        if self.sidebarVisible:
            self.sidebar.place_forget()
            self.sidebarVisible = False
            return

        self.sidebar.place(x=18, y=18, width=92, relheight=1.0, height=-36)
        self.sidebar.lift()
        self.sidebarVisible = True

    def _showPage(self, page_name: str):
        """Show one page and hide the others."""

        pages = {
            "chat": self.chatPage,
            "reminders": self.remindersPage,
            "calendar": self.calendarPage,
        }

        for name, page in pages.items():
            if name == page_name:
                page.pack(fill=BOTH, expand=True)
            else:
                page.pack_forget()

        self.activePage = page_name
        self._setActivePage(page_name)

    def _setActivePage(self, page_name: str):
        """Update sidebar button styles for the active page."""

        buttons = {
            "chat": self.chatNavButton,
            "reminders": self.remindersNavButton,
            "calendar": self.calendarNavButton,
        }

        for name, button in buttons.items():
            is_active = name == page_name
            button.configure(
                bg=ACCENT if is_active else NAV_INACTIVE,
                fg="#08111d" if is_active else TEXT_PRIMARY,
                activebackground=ACCENT_ACTIVE if is_active else NAV_INACTIVE_ACTIVE,
                activeforeground="#08111d" if is_active else TEXT_PRIMARY,
            )

    def _showChatPage(self):
        """Activate the main chat page."""

        self._showPage("chat")
        if self.sidebarVisible:
            self._toggleSidebar()

    def _showRemindersPage(self):
        """Activate the reminders placeholder page."""

        self._showPage("reminders")
        if self.sidebarVisible:
            self._toggleSidebar()

    def _showCalendarPage(self):
        """Activate the calendar placeholder page."""

        self._showPage("calendar")
        if self.sidebarVisible:
            self._toggleSidebar()

    def run(self):
        """Start the Tk event loop."""

        self.inputEntry.focus_set()
        self.root.after(50, self._pollPendingResponses)
        self.root.mainloop()

    def _onSubmitFromKeyboard(self, _event):
        """Submit input when Enter is pressed."""

        self._onSubmit()

    def _onSubmit(self):
        """Dispatch a request to Aura in a background worker."""

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
        """Process a request in a worker thread."""

        try:
            input_manager = self.context.require("inputManager")
            if hasattr(input_manager, "submit"):
                packet = input_manager.submit(user_input, source="windows")
                response = packet.get("response", "")
            else:
                response = input_manager.process(user_input)
            self.pendingResponses.put(("response", str(response)))
        except Exception as error:
            if self.logger:
                self.logger.error(f"Input processing failed: {error}")
            self.pendingResponses.put(("error", str(error)))

    def _pollPendingResponses(self):
        """Flush worker results back onto the UI thread."""

        if self.isClosing:
            return

        try:
            while True:
                result_type, payload = self.pendingResponses.get_nowait()
                if result_type == "response":
                    self._appendTranscript("Aura", payload)
                    self._setBusyState(False)
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
                return

    def _appendTranscript(self, speaker: str, message: str):
        """Append a line to the transcript panel."""

        self.transcript.configure(state=NORMAL)
        self.transcript.insert(END, f"{speaker}: {message}\n\n")
        self.transcript.configure(state=DISABLED)
        self.transcript.see(END)

    def _setBusyState(self, is_busy: bool):
        """Toggle busy-state controls while a request is active."""

        self.isBusy = is_busy
        if is_busy:
            self.sendButton.configure(state=DISABLED, text="Thinking...")
            self.inputEntry.configure(state=DISABLED)
        else:
            self.sendButton.configure(state=NORMAL, text="Send")
            self.inputEntry.configure(state=NORMAL)
            self.inputEntry.focus_set()

    def _showErrorPopup(self, message: str):
        """Display a modal error popup."""

        if self.isClosing:
            return

        try:
            showErrorPopup(self.root, str(message))
        except Exception as error:
            if self.logger:
                self.logger.error(f"Error popup failed: {error}")

    def _closeWindow(self):
        """Destroy the root window safely."""

        if self.isClosing:
            return
        self.isClosing = True
        self.context.should_exit = True
        if self.root.winfo_exists():
            self.root.destroy()
