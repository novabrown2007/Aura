"""Tkinter-based Windows desktop shell for Aura."""

from __future__ import annotations

import calendar as month_calendar
from datetime import date, datetime, timedelta
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
        self.notificationsVisible = False
        self.reminderComposerVisible = False
        self.activePage = "chat"
        self.activeCalendarView = "day"
        self.selectedCalendarDay = date.today()
        self.renderedNotificationItems = []
        self.renderedReminderItems = []
        self.renderedCalendarItems = []

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

        headerActions = Frame(header, bg=WINDOW_BG)
        headerActions.pack(side="right")

        self.profileButton = Button(
            headerActions,
            text="P",
            command=self._onProfilePressed,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=8,
            cursor="hand2",
            width=3,
        )
        self.profileButton.pack(side="right")

        self.notificationButton = Button(
            headerActions,
            text="N",
            command=self._onNotificationPressed,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=8,
            cursor="hand2",
            width=3,
        )
        self.notificationButton.pack(side="right", padx=(0, 8))

        self.pageContainer = Frame(self.contentFrame, bg=WINDOW_BG)
        self.pageContainer.pack(fill=BOTH, expand=True)

        self.chatPage = Frame(self.pageContainer, bg=WINDOW_BG)
        self.remindersPage = Frame(self.pageContainer, bg=WINDOW_BG)
        self.calendarPage = Frame(self.pageContainer, bg=WINDOW_BG)

        self._buildChatPage()
        self._buildRemindersPage()
        self._buildCalendarPage()
        self._buildNotificationsOverlay()
        self._buildReminderComposerOverlay()
        self._buildCalendarEventComposerOverlay()
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

    def _buildRemindersPage(self):
        """Build the reminders page with a list and create action."""

        container = Frame(
            self.remindersPage,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        container.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        header = Frame(container, bg=PANEL_BG)
        header.pack(fill=X, padx=18, pady=(18, 12))

        Label(
            header,
            text="Reminders",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14),
        ).pack(side=LEFT)

        self.createReminderButton = Button(
            header,
            text="New Reminder",
            command=self._toggleReminderComposer,
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            activeforeground="#08111d",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.createReminderButton.pack(side="right")

        self.remindersListContainer = Frame(
            container,
            bg=PANEL_BG,
        )
        self.remindersListContainer.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        self.remindersItemsFrame = Frame(self.remindersListContainer, bg=PANEL_BG)
        self.remindersItemsFrame.pack(fill=BOTH, expand=True)

        self.remindersEmptyLabel = Label(
            self.remindersItemsFrame,
            text="No reminders scheduled yet.",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.remindersEmptyLabel.pack(padx=18, pady=24)

    def _buildCalendarPage(self):
        """Build the calendar day-view page."""

        container = Frame(
            self.calendarPage,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        container.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        header = Frame(container, bg=PANEL_BG)
        header.pack(fill=X, padx=18, pady=(18, 12))

        Label(
            header,
            text="Calendar",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14),
        ).pack(side=LEFT)

        self.createCalendarEventButton = Button(
            header,
            text="New Event",
            command=self._toggleCalendarEventComposer,
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            activeforeground="#08111d",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.createCalendarEventButton.pack(side="right")

        view_row = Frame(container, bg=PANEL_BG)
        view_row.pack(fill=X, padx=18, pady=(0, 10))

        self.calendarViewButtons = {}
        for view_name in ("day", "week", "month", "year"):
            button = Button(
                view_row,
                text=view_name.title(),
                command=lambda selected=view_name: self._setCalendarView(selected),
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
            button.pack(side=LEFT, padx=(0, 8))
            self.calendarViewButtons[view_name] = button

        controls = Frame(container, bg=PANEL_BG)
        controls.pack(fill=X, padx=18, pady=(0, 12))

        self.previousCalendarDayButton = Button(
            controls,
            text="<",
            command=self._showPreviousCalendarRange,
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
        self.previousCalendarDayButton.pack(side=LEFT)

        self.calendarDayEntry = Entry(
            controls,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarDayEntry.pack(side=LEFT, fill=X, expand=True, padx=10, ipady=8)
        self.calendarDayEntry.bind("<Return>", self._onCalendarDaySubmitted)

        self.nextCalendarDayButton = Button(
            controls,
            text=">",
            command=self._showNextCalendarRange,
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
        self.nextCalendarDayButton.pack(side=LEFT)

        self.todayCalendarButton = Button(
            controls,
            text="Today",
            command=self._showTodayCalendarDay,
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
        self.todayCalendarButton.pack(side=LEFT, padx=(10, 0))

        self.loadCalendarDayButton = Button(
            controls,
            text="Load",
            command=self._loadCalendarDayFromEntry,
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
        self.loadCalendarDayButton.pack(side=LEFT, padx=(8, 0))

        self.calendarSummaryLabel = Label(
            container,
            text="",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 12),
        )
        self.calendarSummaryLabel.pack(anchor="w", padx=18, pady=(0, 12))

        self.calendarItemsFrame = Frame(container, bg=PANEL_BG)
        self.calendarItemsFrame.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        self.calendarEmptyLabel = Label(
            self.calendarItemsFrame,
            text="No events, tasks, or reminders for this day.",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.calendarEmptyLabel.pack(padx=18, pady=24)
        self._syncCalendarDayEntry()

    def _buildReminderComposerOverlay(self):
        """Build the in-window reminder creation overlay."""

        self.reminderComposerOverlay = Frame(
            self.contentFrame,
            bg="#0a1017",
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )

        panel = Frame(
            self.reminderComposerOverlay,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        panel.place(relx=0.5, rely=0.5, anchor="center", width=460, height=360)
        self.reminderComposerPanel = panel

        Label(
            panel,
            text="Create Reminder",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14),
        ).pack(anchor="w", padx=18, pady=(18, 12))

        Label(panel, text="Title", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18)
        self.reminderTitleEntry = Entry(
            panel,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.reminderTitleEntry.pack(fill=X, padx=18, pady=(4, 12), ipady=8)

        Label(panel, text="Description", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18)
        self.reminderDescriptionEntry = Entry(
            panel,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.reminderDescriptionEntry.pack(fill=X, padx=18, pady=(4, 12), ipady=8)

        date_time_row = Frame(panel, bg=PANEL_BG)
        date_time_row.pack(fill=X, padx=18, pady=(0, 12))

        date_column = Frame(date_time_row, bg=PANEL_BG)
        date_column.pack(side=LEFT, fill=X, expand=True)
        Label(date_column, text="Date", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        self.reminderDateEntry = Entry(
            date_column,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.reminderDateEntry.pack(fill=X, pady=(4, 0), ipady=8)

        time_column = Frame(date_time_row, bg=PANEL_BG)
        time_column.pack(side=LEFT, fill=X, expand=True, padx=(12, 0))
        Label(time_column, text="Time", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        self.reminderTimeEntry = Entry(
            time_column,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.reminderTimeEntry.pack(fill=X, pady=(4, 0), ipady=8)

        button_row = Frame(panel, bg=PANEL_BG)
        button_row.pack(fill=X, padx=18, pady=(18, 18))

        self.cancelReminderButton = Button(
            button_row,
            text="Cancel",
            command=self._toggleReminderComposer,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.cancelReminderButton.pack(side=LEFT)

        self.confirmReminderButton = Button(
            button_row,
            text="Create",
            command=self._createReminderFromComposer,
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
        self.confirmReminderButton.pack(side="right")

    def _buildCalendarEventComposerOverlay(self):
        """Build the in-window calendar event creation overlay."""

        self.calendarEventComposerVisible = False
        self.calendarEventComposerOverlay = Frame(
            self.contentFrame,
            bg="#0a1017",
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )

        panel = Frame(
            self.calendarEventComposerOverlay,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        panel.place(relx=0.5, rely=0.5, anchor="center", width=520, height=430)

        Label(
            panel,
            text="Create Event",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14),
        ).pack(anchor="w", padx=18, pady=(18, 12))

        Label(panel, text="Title", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18)
        self.calendarEventTitleEntry = Entry(
            panel,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarEventTitleEntry.pack(fill=X, padx=18, pady=(4, 12), ipady=8)

        Label(panel, text="Description", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18)
        self.calendarEventDescriptionEntry = Entry(
            panel,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarEventDescriptionEntry.pack(fill=X, padx=18, pady=(4, 12), ipady=8)

        date_time_row = Frame(panel, bg=PANEL_BG)
        date_time_row.pack(fill=X, padx=18, pady=(0, 12))

        date_column = Frame(date_time_row, bg=PANEL_BG)
        date_column.pack(side=LEFT, fill=X, expand=True)
        Label(date_column, text="Date", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        self.calendarEventDateEntry = Entry(
            date_column,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarEventDateEntry.pack(fill=X, pady=(4, 0), ipady=8)

        start_column = Frame(date_time_row, bg=PANEL_BG)
        start_column.pack(side=LEFT, fill=X, expand=True, padx=(12, 0))
        Label(start_column, text="Start", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        self.calendarEventStartEntry = Entry(
            start_column,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarEventStartEntry.pack(fill=X, pady=(4, 0), ipady=8)

        end_column = Frame(date_time_row, bg=PANEL_BG)
        end_column.pack(side=LEFT, fill=X, expand=True, padx=(12, 0))
        Label(end_column, text="End", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        self.calendarEventEndEntry = Entry(
            end_column,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarEventEndEntry.pack(fill=X, pady=(4, 0), ipady=8)

        Label(panel, text="Location", bg=PANEL_BG, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18)
        self.calendarEventLocationEntry = Entry(
            panel,
            bg=INPUT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarEventLocationEntry.pack(fill=X, padx=18, pady=(4, 12), ipady=8)

        button_row = Frame(panel, bg=PANEL_BG)
        button_row.pack(fill=X, padx=18, pady=(8, 18))

        self.cancelCalendarEventButton = Button(
            button_row,
            text="Cancel",
            command=self._toggleCalendarEventComposer,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 10),
            padx=14,
            pady=8,
            cursor="hand2",
        )
        self.cancelCalendarEventButton.pack(side=LEFT)

        self.confirmCalendarEventButton = Button(
            button_row,
            text="Create",
            command=self._createCalendarEventFromComposer,
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
        self.confirmCalendarEventButton.pack(side="right")

    def _buildNotificationsOverlay(self):
        """Build the persistent notifications overlay and content holder."""

        self.notificationsOverlay = Frame(
            self.contentFrame,
            bg="#0a1017",
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )

        header = Frame(self.notificationsOverlay, bg="#0a1017")
        header.pack(fill=X, padx=18, pady=(16, 10))

        Label(
            header,
            text="Notifications",
            bg="#0a1017",
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 14),
        ).pack(side=LEFT)

        self.closeNotificationsButton = Button(
            header,
            text="Close",
            command=self._toggleNotificationsOverlay,
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            activebackground=NAV_INACTIVE_ACTIVE,
            activeforeground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 9),
            padx=12,
            pady=6,
            cursor="hand2",
        )
        self.closeNotificationsButton.pack(side="right")

        self.notificationsListContainer = Frame(
            self.notificationsOverlay,
            bg=PANEL_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        self.notificationsListContainer.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        self.notificationsItemsFrame = Frame(self.notificationsListContainer, bg=PANEL_BG)
        self.notificationsItemsFrame.pack(fill=BOTH, expand=True, padx=14, pady=14)

        self.notificationsEmptyLabel = Label(
            self.notificationsItemsFrame,
            text="No notifications to display yet.",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.notificationsEmptyLabel.pack(padx=18, pady=24)

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
        if page_name == "reminders":
            self._refreshRemindersList()
        if page_name == "calendar":
            self._refreshCalendarView()

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
        """Activate the calendar page."""

        self._showPage("calendar")
        if self.sidebarVisible:
            self._toggleSidebar()

    def _setCalendarView(self, view_name: str):
        """Switch between calendar view modes."""

        if view_name not in {"day", "week", "month", "year"}:
            return

        self.activeCalendarView = view_name
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _showPreviousCalendarRange(self):
        """Move the selected calendar date back by the active view size."""

        if self.activeCalendarView == "day":
            self.selectedCalendarDay -= timedelta(days=1)
        elif self.activeCalendarView == "week":
            self.selectedCalendarDay -= timedelta(days=7)
        elif self.activeCalendarView == "month":
            self.selectedCalendarDay = self._addMonths(self.selectedCalendarDay, -1)
        else:
            self.selectedCalendarDay = self._addMonths(self.selectedCalendarDay, -12)

        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _showNextCalendarRange(self):
        """Move the selected calendar date forward by the active view size."""

        if self.activeCalendarView == "day":
            self.selectedCalendarDay += timedelta(days=1)
        elif self.activeCalendarView == "week":
            self.selectedCalendarDay += timedelta(days=7)
        elif self.activeCalendarView == "month":
            self.selectedCalendarDay = self._addMonths(self.selectedCalendarDay, 1)
        else:
            self.selectedCalendarDay = self._addMonths(self.selectedCalendarDay, 12)

        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _showTodayCalendarDay(self):
        """Return the calendar to today."""

        self.selectedCalendarDay = date.today()
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _onCalendarDaySubmitted(self, _event):
        """Load the date typed in the calendar date field."""

        self._loadCalendarDayFromEntry()

    def _loadCalendarDayFromEntry(self):
        """Parse the calendar date entry and refresh the active view."""

        try:
            self.selectedCalendarDay = self._parseCalendarDate(self.calendarDayEntry.get())
        except ValueError as error:
            self._showErrorPopup(str(error))
            return

        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _refreshCalendarView(self):
        """Reload calendar data for the active view and repaint the list."""

        self._setActiveCalendarViewButton()

        calendar_service = getattr(self.context, "calendar", None)
        if calendar_service is None:
            self._renderCalendarSections([], "Calendar is not available.")
            return

        try:
            view_data = self._loadCalendarViewData(calendar_service)
        except Exception as error:
            self._renderCalendarSections([], "Calendar could not be loaded.")
            self._showErrorPopup(str(error))
            return

        sections = self._buildCalendarSections(view_data)
        self._renderCalendarSections(sections, self._buildCalendarSummary(view_data))

    def _loadCalendarViewData(self, calendar_service):
        """Call the backend calendar method for the active view."""

        selected_day = self.selectedCalendarDay.strftime("%Y-%m-%d")

        if self.activeCalendarView == "day":
            return dict(calendar_service.buildDayView(selected_day))
        if self.activeCalendarView == "week":
            return dict(calendar_service.buildWeekView(selected_day))
        if self.activeCalendarView == "month":
            return dict(calendar_service.buildMonthView(selected_day))

        months = []
        total_events = []
        total_tasks = []
        total_reminders = []
        for month_index in range(1, 13):
            month_day = date(self.selectedCalendarDay.year, month_index, 1).strftime("%Y-%m-%d")
            month_view = dict(calendar_service.buildMonthView(month_day))
            months.append(month_view)
            total_events.extend(month_view.get("events", []))
            total_tasks.extend(month_view.get("tasks", []))
            total_reminders.extend(month_view.get("reminders", []))

        return {
            "year": str(self.selectedCalendarDay.year),
            "months": months,
            "events": total_events,
            "tasks": total_tasks,
            "reminders": total_reminders,
        }

    def _buildCalendarSummary(self, view_data):
        """Build the status line for the active calendar view."""

        event_count = len(view_data.get("events", []))
        task_count = len(view_data.get("tasks", []))
        reminder_count = len(view_data.get("reminders", []))

        if self.activeCalendarView == "day":
            label = self.selectedCalendarDay.strftime("%A, %B %d, %Y")
        elif self.activeCalendarView == "week":
            label = f"{view_data.get('week_start')} to {view_data.get('week_end')}"
        elif self.activeCalendarView == "month":
            label = self.selectedCalendarDay.strftime("%B %Y")
        else:
            label = str(self.selectedCalendarDay.year)

        return f"{label} - {event_count} events, {task_count} tasks, {reminder_count} reminders"

    def _buildCalendarSections(self, view_data):
        """Convert backend calendar data into renderable sections."""

        if self.activeCalendarView == "year":
            sections = []
            for month_view in view_data.get("months", []):
                rows = (
                    self._calendarRowsForKind("Event", month_view.get("events", []))
                    + self._calendarRowsForKind("Task", month_view.get("tasks", []))
                    + self._calendarRowsForKind("Reminder", month_view.get("reminders", []))
                )
                if rows:
                    month_label = self._formatMonthLabel(month_view.get("month"))
                    sections.append({"title": month_label, "rows": rows})
            return sections

        return [
            {"title": "Events", "rows": self._calendarRowsForKind("Event", view_data.get("events", []))},
            {"title": "Tasks", "rows": self._calendarRowsForKind("Task", view_data.get("tasks", []))},
            {"title": "Reminders", "rows": self._calendarRowsForKind("Reminder", view_data.get("reminders", []))},
        ]

    def _calendarRowsForKind(self, kind: str, rows):
        """Normalize calendar rows for display."""

        normalized = []
        for row in rows:
            item = dict(row)
            if kind == "Event":
                when_value = item.get("start_at")
                detail = item.get("location") or item.get("description") or ""
            elif kind == "Task":
                when_value = item.get("due_at")
                detail = item.get("description") or item.get("priority") or item.get("status") or ""
            else:
                when_value = item.get("remind_at")
                detail = item.get("notes") or ""

            normalized.append(
                {
                    "kind": kind,
                    "title": str(item.get("title") or f"Untitled {kind.lower()}"),
                    "when": self._formatCalendarTimestamp(when_value),
                    "sort_key": str(when_value or ""),
                    "detail": str(detail or ""),
                    "row": item,
                }
            )

        normalized.sort(key=lambda item: (item["sort_key"], item["title"]))
        return normalized

    def _renderCalendarSections(self, sections, summary_text: str):
        """Render the calendar sections for the active view."""

        for item in self.renderedCalendarItems:
            item["container"].destroy()
        self.renderedCalendarItems = []

        self.calendarSummaryLabel.configure(text=summary_text)
        has_rows = any(section["rows"] for section in sections)
        if not has_rows:
            self.calendarEmptyLabel.pack(padx=18, pady=24)
            return

        self.calendarEmptyLabel.pack_forget()
        for section in sections:
            if not section["rows"]:
                continue

            section_container = Frame(self.calendarItemsFrame, bg=PANEL_BG)
            section_container.pack(fill=X, pady=(0, 12))

            Label(
                section_container,
                text=section["title"],
                bg=PANEL_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI Semibold", 10),
            ).pack(anchor="w", pady=(0, 6))

            for row in section["rows"]:
                card = Frame(
                    section_container,
                    bg=TRANSCRIPT_BG,
                    highlightbackground=BORDER,
                    highlightthickness=1,
                    bd=0,
                )
                card.pack(fill=X, pady=(0, 8))

                top_row = Frame(card, bg=TRANSCRIPT_BG)
                top_row.pack(fill=X, padx=12, pady=(10, 4))

                Label(
                    top_row,
                    text=f"{row['kind']}: {row['title']}",
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_PRIMARY,
                    font=("Segoe UI Semibold", 11),
                ).pack(side=LEFT)

                Label(
                    card,
                    text=row["when"],
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_MUTED,
                    font=("Segoe UI", 9),
                ).pack(anchor="w", padx=12)

                if row["detail"]:
                    Label(
                        card,
                        text=row["detail"],
                        bg=TRANSCRIPT_BG,
                        fg=TEXT_PRIMARY,
                        font=("Segoe UI", 10),
                        justify="left",
                        wraplength=560,
                    ).pack(anchor="w", fill=X, padx=12, pady=(6, 10))

                self.renderedCalendarItems.append({"row": row, "container": card})

            self.renderedCalendarItems.append({"row": {"section": section["title"]}, "container": section_container})

    def _toggleCalendarEventComposer(self):
        """Show or hide the event creation overlay."""

        if self.calendarEventComposerVisible:
            self.calendarEventComposerOverlay.place_forget()
            self.calendarEventComposerVisible = False
            return

        self.calendarEventDateEntry.delete(0, END)
        self.calendarEventDateEntry.insert(0, self.selectedCalendarDay.strftime("%Y-%m-%d"))
        self.calendarEventComposerOverlay.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self.calendarEventComposerOverlay.lift()
        self.calendarEventComposerVisible = True
        self.calendarEventTitleEntry.focus_set()

    def _createCalendarEventFromComposer(self):
        """Create one calendar event from the composer inputs."""

        title = self.calendarEventTitleEntry.get().strip()
        description = self.calendarEventDescriptionEntry.get().strip()
        date_value = self.calendarEventDateEntry.get().strip()
        start_value = self.calendarEventStartEntry.get().strip()
        end_value = self.calendarEventEndEntry.get().strip()
        location = self.calendarEventLocationEntry.get().strip()

        if not title:
            self._showErrorPopup("Event title is required.")
            return
        if not date_value or not start_value:
            self._showErrorPopup("Event date and start time are required.")
            return

        try:
            event_day = self._parseCalendarDate(date_value)
            start_at = f"{event_day.strftime('%Y-%m-%d')} {start_value}"
            end_at = f"{event_day.strftime('%Y-%m-%d')} {end_value}" if end_value else None
            calendar_service = self.context.require("calendar")
            calendar_service.createEvent(
                title=title,
                description=description,
                location=location,
                start_at=start_at,
                end_at=end_at,
            )
        except Exception as error:
            self._showErrorPopup(str(error))
            return

        for entry in (
            self.calendarEventTitleEntry,
            self.calendarEventDescriptionEntry,
            self.calendarEventDateEntry,
            self.calendarEventStartEntry,
            self.calendarEventEndEntry,
            self.calendarEventLocationEntry,
        ):
            entry.delete(0, END)

        self.selectedCalendarDay = event_day
        self._toggleCalendarEventComposer()
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _setActiveCalendarViewButton(self):
        """Update calendar view button styling."""

        for view_name, button in self.calendarViewButtons.items():
            is_active = view_name == self.activeCalendarView
            button.configure(
                bg=ACCENT if is_active else NAV_INACTIVE,
                fg="#08111d" if is_active else TEXT_PRIMARY,
                activebackground=ACCENT_ACTIVE if is_active else NAV_INACTIVE_ACTIVE,
                activeforeground="#08111d" if is_active else TEXT_PRIMARY,
            )

    def _syncCalendarDayEntry(self):
        """Write the selected date into the calendar date entry."""

        if not hasattr(self, "calendarDayEntry"):
            return

        self.calendarDayEntry.delete(0, END)
        self.calendarDayEntry.insert(0, self.selectedCalendarDay.strftime("%Y-%m-%d"))

    def _parseCalendarDate(self, raw_value: str) -> date:
        """Parse a user-entered calendar date."""

        value = str(raw_value or "").strip()
        for format_string in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, format_string).date()
            except ValueError:
                continue
        raise ValueError("Invalid date value. Use YYYY-MM-DD or DD/MM/YYYY.")

    def _formatCalendarTimestamp(self, timestamp_value):
        """Format calendar timestamp text for display."""

        if not timestamp_value:
            return "Unscheduled"

        dt_util = getattr(self.context, "dtUtil", None)
        if dt_util is not None and hasattr(dt_util, "toPreferredDateTime"):
            try:
                return dt_util.toPreferredDateTime(str(timestamp_value))
            except Exception:
                return str(timestamp_value)
        return str(timestamp_value)

    @staticmethod
    def _formatMonthLabel(month_value):
        """Format a backend month value like YYYY-MM."""

        try:
            parsed = datetime.strptime(str(month_value), "%Y-%m")
            return parsed.strftime("%B %Y")
        except ValueError:
            return str(month_value or "Month")

    @staticmethod
    def _addMonths(value: date, offset: int) -> date:
        """Add whole months while preserving a valid day of month."""

        total_month = value.month - 1 + offset
        year = value.year + total_month // 12
        month = total_month % 12 + 1
        day = min(value.day, month_calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    def _onNotificationPressed(self):
        """Handle notification-button presses."""

        self._toggleNotificationsOverlay()

    def _toggleNotificationsOverlay(self):
        """Show or hide the notifications overlay."""

        if self.notificationsVisible:
            self.notificationsOverlay.place_forget()
            self.notificationsVisible = False
            return

        self._refreshNotificationsOverlay()
        self.notificationsOverlay.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self.notificationsOverlay.lift()
        self.notificationsVisible = True

    def _refreshNotificationsOverlay(self):
        """Reload persisted notifications and repaint the overlay list."""

        notifications_service = getattr(self.context, "notifications", None)
        rows = []
        if notifications_service is not None and hasattr(notifications_service, "listNotifications"):
            rows = notifications_service.listNotifications()
        self._renderNotificationRows(rows)

    def _renderNotificationRows(self, rows):
        """Render notifications in newest-first order."""

        for item in self.renderedNotificationItems:
            item["container"].destroy()
        self.renderedNotificationItems = []

        ordered_rows = sorted(
            [dict(row) for row in rows],
            key=lambda row: (str(row.get("notification_at") or ""), int(row.get("id") or 0)),
            reverse=True,
        )

        if not ordered_rows:
            self.notificationsEmptyLabel.pack(padx=18, pady=24)
            return

        self.notificationsEmptyLabel.pack_forget()

        for row in ordered_rows:
            card = Frame(
                self.notificationsItemsFrame,
                bg=TRANSCRIPT_BG,
                highlightbackground=BORDER,
                highlightthickness=1,
                bd=0,
            )
            card.pack(fill=X, pady=(0, 10))

            top_row = Frame(card, bg=TRANSCRIPT_BG)
            top_row.pack(fill=X, padx=12, pady=(12, 6))

            Label(
                top_row,
                text=str(row.get("title") or "Untitled notification"),
                bg=TRANSCRIPT_BG,
                fg=TEXT_PRIMARY,
                font=("Segoe UI Semibold", 11),
            ).pack(side=LEFT)

            Button(
                top_row,
                text="x",
                command=lambda notification_id=int(row.get("id") or 0): self._deleteNotification(notification_id),
                bg=NAV_INACTIVE,
                fg=TEXT_PRIMARY,
                activebackground=NAV_INACTIVE_ACTIVE,
                activeforeground=TEXT_PRIMARY,
                relief="flat",
                bd=0,
                font=("Segoe UI Semibold", 9),
                padx=8,
                pady=3,
                cursor="hand2",
            ).pack(side="right")

            Label(
                card,
                text=self._formatNotificationTimestamp(row.get("notification_at")),
                bg=TRANSCRIPT_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI", 9),
            ).pack(anchor="w", padx=12)

            Label(
                card,
                text=str(row.get("content") or ""),
                bg=TRANSCRIPT_BG,
                fg=TEXT_PRIMARY,
                font=("Segoe UI", 10),
                justify="left",
                wraplength=520,
            ).pack(anchor="w", fill=X, padx=12, pady=(6, 12))

            self.renderedNotificationItems.append({"row": row, "container": card})

    def _formatNotificationTimestamp(self, timestamp_value):
        """Convert one stored notification timestamp into the preferred display format."""

        if not timestamp_value:
            return "Unscheduled"

        dt_util = getattr(self.context, "dtUtil", None)
        if dt_util is None or not hasattr(dt_util, "toPreferredDateTime"):
            return str(timestamp_value)

        try:
            return dt_util.toPreferredDateTime(str(timestamp_value))
        except Exception:
            return str(timestamp_value)

    def _deleteNotification(self, notification_id: int):
        """Delete one notification and refresh the overlay list."""

        if notification_id <= 0:
            return

        notifications_service = self.context.require("notifications")
        notifications_service.deleteNotification(notification_id)
        self._refreshNotificationsOverlay()

    def _onProfilePressed(self):
        """Handle profile-button presses."""

        return None

    def _toggleReminderComposer(self):
        """Show or hide the reminder creation overlay."""

        if self.reminderComposerVisible:
            self.reminderComposerOverlay.place_forget()
            self.reminderComposerVisible = False
            return

        self.reminderComposerOverlay.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self.reminderComposerOverlay.lift()
        self.reminderComposerVisible = True
        self.reminderTitleEntry.focus_set()

    def _createReminderFromComposer(self):
        """Create one reminder from the composer overlay inputs."""

        title = self.reminderTitleEntry.get().strip()
        content = self.reminderDescriptionEntry.get().strip()
        date_value = self.reminderDateEntry.get().strip()
        time_value = self.reminderTimeEntry.get().strip()

        if not title:
            self._showErrorPopup("Reminder title is required.")
            return
        if not date_value or not time_value:
            self._showErrorPopup("Reminder date and time are required.")
            return

        try:
            reminder_at = f"{time_value} {date_value}"
            reminders_service = self.context.require("reminders")
            reminders_service.createReminder(
                title=title,
                content=content,
                module_of_origin="windows",
                reminder_at=reminder_at,
            )
        except Exception as error:
            self._showErrorPopup(str(error))
            return

        self.reminderTitleEntry.delete(0, END)
        self.reminderDescriptionEntry.delete(0, END)
        self.reminderDateEntry.delete(0, END)
        self.reminderTimeEntry.delete(0, END)
        self._toggleReminderComposer()
        self._refreshRemindersList()

    def _refreshRemindersList(self):
        """Reload persisted reminders and repaint the reminders page."""

        reminders_service = getattr(self.context, "reminders", None)
        rows = []
        if reminders_service is not None and hasattr(reminders_service, "listReminders"):
            rows = reminders_service.listReminders()
        self._renderReminderRows(rows)

    def _renderReminderRows(self, rows):
        """Render the reminders page list."""

        for item in self.renderedReminderItems:
            item["container"].destroy()
        self.renderedReminderItems = []

        ordered_rows = sorted(
            [dict(row) for row in rows],
            key=lambda row: (str(row.get("reminder_at") or ""), int(row.get("id") or 0)),
        )

        if not ordered_rows:
            self.remindersEmptyLabel.pack(padx=18, pady=24)
            return

        self.remindersEmptyLabel.pack_forget()

        for row in ordered_rows:
            card = Frame(
                self.remindersItemsFrame,
                bg=TRANSCRIPT_BG,
                highlightbackground=BORDER,
                highlightthickness=1,
                bd=0,
            )
            card.pack(fill=X, pady=(0, 10))

            Label(
                card,
                text=str(row.get("title") or "Untitled reminder"),
                bg=TRANSCRIPT_BG,
                fg=TEXT_PRIMARY,
                font=("Segoe UI Semibold", 11),
            ).pack(anchor="w", padx=12, pady=(12, 4))

            Label(
                card,
                text=self._formatReminderTimestamp(row.get("reminder_at")),
                bg=TRANSCRIPT_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI", 9),
            ).pack(anchor="w", padx=12)

            Label(
                card,
                text=str(row.get("content") or ""),
                bg=TRANSCRIPT_BG,
                fg=TEXT_PRIMARY,
                font=("Segoe UI", 10),
                justify="left",
                wraplength=560,
            ).pack(anchor="w", fill=X, padx=12, pady=(6, 12))

            self.renderedReminderItems.append({"row": row, "container": card})

    def _formatReminderTimestamp(self, timestamp_value):
        """Convert one stored reminder timestamp into the preferred display format."""

        if not timestamp_value:
            return "Unscheduled"

        dt_util = getattr(self.context, "dtUtil", None)
        if dt_util is None or not hasattr(dt_util, "toPreferredDateTime"):
            return str(timestamp_value)

        try:
            return dt_util.toPreferredDateTime(str(timestamp_value))
        except Exception:
            return str(timestamp_value)

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
