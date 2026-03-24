"""Tkinter-based Windows desktop application for Aura.

This module defines the primary GUI class used by the Windows interface
branch. It provides:
- A conversation transcript panel
- A text input box for prompts/commands
- A send button with busy-state handling
- Background processing so the UI remains responsive
"""

from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
import sys
from threading import Thread
from tkinter import (
    END,
    DISABLED,
    NORMAL,
    BOTH,
    TOP,
    LEFT,
    RIGHT,
    X,
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
SIDEBAR_BG = "#0d1219"
TEXT_PRIMARY = "#e8eef7"
TEXT_MUTED = "#93a1b5"
ACCENT = "#3ea6ff"
ACCENT_ACTIVE = "#68bcff"
BORDER = "#243042"
USER_TEXT = "#f6d37a"
ERROR_TEXT = "#ff8f8f"
NAV_INACTIVE = "#192230"
NAV_INACTIVE_ACTIVE = "#233244"
WINDOW_ICON_RELATIVE_PATH = Path("assets") / "icons" / "aura.ico"
PLACEHOLDER_TEXT = "Coming soon."


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
        self.sidebarVisible = False
        self.activePage = "chat"

        self.root = Tk()
        self.root.title("Aura Assistant")
        self.root.geometry("900x620")
        self.root.minsize(760, 500)
        self.root.configure(bg=WINDOW_BG)
        self.root.protocol("WM_DELETE_WINDOW", self._onWindowClose)
        self._applyWindowIcon()

        self._buildLayout()
        self._subscribeToReminderEvents()
        self._appendTranscript("Aura", "Windows interface initialized.")
        for warning in getattr(self.context, "bootstrapWarnings", []):
            self._appendTranscript("Aura", f"Startup warning: {warning}")

        if self.logger:
            self.logger.info("AuraWindowsApp initialized.")

    def _applyWindowIcon(self):
        """Apply the Windows app icon when the `.ico` asset is available."""

        icon_path = self._resolveWindowIconPath()
        if not icon_path.exists():
            return

        try:
            self.root.iconbitmap(default=str(icon_path))
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Window icon load failed: {error}")

    def _resolveWindowIconPath(self) -> Path:
        """Resolve the icon path for both source and frozen executable modes."""

        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / WINDOW_ICON_RELATIVE_PATH

        return Path(__file__).resolve().parents[4] / WINDOW_ICON_RELATIVE_PATH

    def _buildLayout(self):
        """Create and arrange all Tkinter widgets for the chat interface."""

        self.shell = Frame(self.root, bg=WINDOW_BG)
        self.shell.pack(fill=BOTH, expand=True)

        self.contentFrame = Frame(self.shell, bg=WINDOW_BG)
        self.contentFrame.pack(side=LEFT, fill=BOTH, expand=True, pady=18, padx=18)

        self.sidebar = Frame(
            self.shell,
            bg=SIDEBAR_BG,
            width=84,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        self.sidebar.pack_propagate(False)

        sidebar_title = Label(
            self.sidebar,
            text="A",
            bg=SIDEBAR_BG,
            fg=ACCENT,
            font=("Segoe UI Semibold", 22),
        )
        sidebar_title.pack(pady=(18, 26))

        self.chatNavButton = self._createSidebarButton(
            self.sidebar,
            icon="...",
            label="Chat",
            active=True,
            command=self._showChatPage,
        )
        self.chatNavButton.pack(side=TOP, fill=X, padx=12, pady=(0, 10))

        self.remindersNavButton = self._createSidebarButton(
            self.sidebar,
            icon="R",
            label="Reminders",
            active=False,
            command=self._showRemindersPage,
        )
        self.remindersNavButton.pack(side=TOP, fill=X, padx=12, pady=(0, 10))

        self.calendarNavButton = self._createSidebarButton(
            self.sidebar,
            icon="[]",
            label="Calendar",
            active=False,
            command=self._showCalendarPage,
        )
        self.calendarNavButton.pack(side=TOP, fill=X, padx=12, pady=(0, 10))

        header = Frame(self.contentFrame, bg=WINDOW_BG)
        header.pack(fill=X, pady=(0, 10))

        title_label = Label(
            header,
            text="Aura",
            bg=WINDOW_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 18),
        )

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

        title_label.pack(side=LEFT)

        subtitle_label = Label(
            header,
            text="Windows desktop interface",
            bg=WINDOW_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        subtitle_label.pack(side=RIGHT, pady=(6, 0))

        self.pageContainer = Frame(self.contentFrame, bg=WINDOW_BG)
        self.pageContainer.pack(fill=BOTH, expand=True)

        self.chatPage = Frame(self.pageContainer, bg=WINDOW_BG)
        self.remindersPage = Frame(self.pageContainer, bg=WINDOW_BG)
        self.calendarPage = Frame(self.pageContainer, bg=WINDOW_BG)

        self._buildChatPage()
        self._buildRemindersPage()
        self._buildCalendarPage()
        self._showPage("chat")

    def _subscribeToReminderEvents(self):
        """Subscribe the Windows UI to runtime reminder notifications."""

        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is None:
            return

        event_manager.subscribe("reminder_triggered", self._onReminderTriggered)

    def _buildChatPage(self):
        """Build the chat page widgets."""

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
            selectbackground=ACCENT,
            selectforeground="#08111d",
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
        self.sendButton.pack(side=RIGHT, padx=(12, 0))

    def _buildRemindersPage(self):
        """Build the reminders management page widgets."""

        controls_container = Frame(
            self.remindersPage,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        controls_container.pack(fill=X, padx=18, pady=(0, 10))

        controls_inner = Frame(controls_container, bg=PANEL_BG)
        controls_inner.pack(fill=X, padx=14, pady=14)

        reminders_label = Label(
            controls_inner,
            text="Manage reminders",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 12),
        )
        reminders_label.pack(anchor="w", pady=(0, 10))

        reminder_title_label = Label(
            controls_inner,
            text="Reminder title",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        reminder_title_label.pack(anchor="w", pady=(0, 6))

        self.reminderTitleEntry = Entry(
            controls_inner,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.reminderTitleEntry.pack(fill=X, pady=(0, 10), ipady=10)

        reminder_when_label = Label(
            controls_inner,
            text="Remind at (optional, format: HH:MM DD/MM/YYYY or HH:MM)",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        reminder_when_label.pack(anchor="w", pady=(0, 6))

        self.reminderWhenEntry = Entry(
            controls_inner,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.reminderWhenEntry.pack(fill=X, pady=(0, 10), ipady=10)

        reminder_actions = Frame(controls_inner, bg=PANEL_BG)
        reminder_actions.pack(fill=X, pady=(0, 8))

        self.addReminderButton = Button(
            reminder_actions,
            text="Add Reminder",
            command=self._addReminder,
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            activeforeground="#08111d",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=16,
            pady=8,
            cursor="hand2",
        )
        self.addReminderButton.pack(side=LEFT)

        self.refreshRemindersButton = Button(
            reminder_actions,
            text="Refresh",
            command=self._refreshRemindersList,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 10),
            padx=16,
            pady=8,
            cursor="hand2",
        )
        self.refreshRemindersButton.pack(side=LEFT, padx=(10, 0))

        reminder_delete_row = Frame(controls_inner, bg=PANEL_BG)
        reminder_delete_row.pack(fill=X)

        delete_reminder_label = Label(
            controls_inner,
            text="Delete reminder by ID",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        )
        delete_reminder_label.pack(anchor="w", pady=(4, 6))

        self.deleteReminderEntry = Entry(
            reminder_delete_row,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.deleteReminderEntry.pack(side=LEFT, fill=X, expand=True, ipady=10)

        self.deleteReminderButton = Button(
            reminder_delete_row,
            text="Delete",
            command=self._deleteReminder,
            bg="#4b2230",
            fg="#ffd5de",
            activebackground="#663142",
            activeforeground="#ffe5eb",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=16,
            pady=8,
            cursor="hand2",
        )
        self.deleteReminderButton.pack(side=RIGHT, padx=(10, 0))

        reminders_list_container = Frame(
            self.remindersPage,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        reminders_list_container.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        self.remindersTranscript = ScrolledText(
            reminders_list_container,
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
        self.remindersTranscript.pack(fill=BOTH, expand=True, padx=1, pady=1)

    def _buildCalendarPage(self):
        """Build the calendar placeholder page."""

        placeholder_container = Frame(
            self.calendarPage,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        placeholder_container.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        placeholder_label = Label(
            placeholder_container,
            text=PLACEHOLDER_TEXT,
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 12),
        )
        placeholder_label.pack(pady=40)

    def _createSidebarButton(self, parent, icon: str, label: str, active: bool, command):
        """Create a sidebar navigation button with active/inactive styling.

        Args:
            parent:
                Parent Tk widget.
            icon (str):
                Short icon glyph or text marker.
            label (str):
                Button label.
            active (bool):
                Whether this button represents the current page.
            command:
                Callback executed when button is clicked.
        """

        bg = ACCENT if active else NAV_INACTIVE
        fg = "#08111d" if active else TEXT_PRIMARY
        active_bg = ACCENT_ACTIVE if active else NAV_INACTIVE_ACTIVE

        return Button(
            parent,
            text=f"{icon}\n{label}",
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=8,
            pady=12,
            cursor="hand2",
            justify="center",
        )

    def _setActivePage(self, page_name: str):
        """Update sidebar button styles for the selected page.

        Args:
            page_name (str):
                Active page identifier.
        """

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

    def _showPage(self, page_name: str):
        """Show one page and hide the others.

        Args:
            page_name (str):
                Active page identifier.
        """

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

    def _toggleSidebar(self):
        """Show or hide the navigation sidebar drawer."""

        if self.sidebarVisible:
            self.sidebar.place_forget()
            self.sidebarVisible = False
            return

        self.sidebar.place(x=18, y=18, width=84, relheight=1.0, height=-36)
        self.sidebar.lift()
        self.sidebarVisible = True

    def run(self):
        """Start the Windows UI event loop."""

        self.inputEntry.focus_set()
        self.root.after(50, self._pollPendingResponses)
        self.root.mainloop()

    def _onSubmitFromKeyboard(self, _event):
        """Handle Enter key submission from the input field."""

        self._onSubmit()

    def _showChatPage(self):
        """Activate the chat page in the sidebar.

        The chat surface is the only implemented page at the moment.
        """

        self._showPage("chat")
        if self.sidebarVisible:
            self._toggleSidebar()

    def _showRemindersPage(self):
        """Activate the reminders page and refresh its data from storage."""

        self._showPage("reminders")
        self._refreshRemindersList()
        if self.sidebarVisible:
            self._toggleSidebar()

    def _showCalendarPage(self):
        """Activate the calendar placeholder button without changing content."""

        self._showPage("calendar")
        if self.sidebarVisible:
            self._toggleSidebar()

    def _getRemindersManager(self):
        """Return the reminders manager if it exists."""

        return getattr(self.context, "reminders", None)

    def _refreshRemindersList(self):
        """Refresh the reminders page from the reminders backend."""

        reminders = self._getRemindersManager()
        if reminders is None:
            content = "Reminders module is unavailable."
        else:
            try:
                rows = reminders.listReminders()
                if not rows:
                    content = "No reminders found."
                else:
                    lines = ["------ REMINDERS ------"]
                    for row in rows:
                        reminder_id = row.get("id")
                        title = row.get("title")
                        remind_at = row.get("remind_at") or "unscheduled"
                        created_at = row.get("created_at") or "unknown"
                        lines.append(f"{reminder_id}: {title}")
                        lines.append(f"  at: {remind_at}")
                        lines.append(f"  created: {created_at}")
                        lines.append("")
                    content = "\n".join(lines).rstrip()
            except Exception as error:
                self._showErrorPopup(str(error))
                content = f"Error loading reminders: {error}"

        self.remindersTranscript.configure(state=NORMAL)
        self.remindersTranscript.delete("1.0", END)
        self.remindersTranscript.insert(END, content)
        self.remindersTranscript.configure(state=DISABLED)

    def _addReminder(self):
        """Create a reminder from the reminders page input fields."""

        title = self.reminderTitleEntry.get().strip()
        remind_at = self.reminderWhenEntry.get().strip() or None
        if not title:
            self._showErrorPopup("Reminder title is required.")
            return

        reminders = self._getRemindersManager()
        if reminders is None:
            self._showErrorPopup("Reminders module is unavailable.")
            return

        try:
            reminders.createReminder(title=title, remind_at=remind_at)
            self.reminderTitleEntry.delete(0, END)
            self.reminderWhenEntry.delete(0, END)
            self._refreshRemindersList()
        except Exception as error:
            self._showErrorPopup(str(error))

    def _deleteReminder(self):
        """Delete a reminder using the ID entered on the reminders page."""

        raw_id = self.deleteReminderEntry.get().strip()
        if not raw_id:
            self._showErrorPopup("Reminder ID is required.")
            return

        try:
            reminder_id = int(raw_id)
        except ValueError:
            self._showErrorPopup("Reminder ID must be a number.")
            return

        reminders = self._getRemindersManager()
        if reminders is None:
            self._showErrorPopup("Reminders module is unavailable.")
            return

        try:
            reminders.deleteReminder(reminder_id)
            self.deleteReminderEntry.delete(0, END)
            self._refreshRemindersList()
        except Exception as error:
            self._showErrorPopup(str(error))

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
                elif result_type == "reminder":
                    self._appendTranscript("Reminder", payload)
                    self._showReminderPopup(payload)
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
        elif speaker == "Reminder":
            speaker_color = ACCENT_ACTIVE
        elif speaker == "Aura" and str(message).startswith("Error:"):
            speaker_color = ERROR_TEXT

        self.transcript.configure(state=NORMAL)
        self.transcript.insert(END, f"{speaker}: ", speaker.lower())
        self.transcript.insert(END, f"{message}\n\n")
        self.transcript.tag_configure("you", foreground=USER_TEXT, font=("Segoe UI Semibold", 10))
        self.transcript.tag_configure("reminder", foreground=ACCENT_ACTIVE, font=("Segoe UI Semibold", 10))
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

    def _onReminderTriggered(self, event):
        """Queue reminder events onto the Tk thread for safe UI rendering."""

        data = getattr(event, "data", {}) or {}
        title = data.get("title", "Reminder")
        remind_at = data.get("remind_at")
        if remind_at:
            message = f"{title} ({remind_at})"
        else:
            message = str(title)
        self.pendingResponses.put(("reminder", message))

    def _showReminderPopup(self, message: str):
        """Display a modal popup when a reminder becomes due."""

        if self.isClosing:
            return

        try:
            messagebox.showinfo("Aura Reminder", str(message), parent=self.root)
        except Exception as error:
            if self.logger:
                self.logger.error(f"Reminder popup failed: {error}")
