"""Tkinter-based Windows desktop shell for Aura."""

from __future__ import annotations

import calendar as month_calendar
import json
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
        self.selectedCalendarId = None
        self.calendarSearchActive = False
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

        self.calendarBodyFrame = Frame(container, bg=PANEL_BG)
        self.calendarBodyFrame.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        self.calendarSidePanel = Frame(
            self.calendarBodyFrame,
            bg=TRANSCRIPT_BG,
            width=220,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        self.calendarSidePanel.pack(side=LEFT, fill="y", padx=(0, 12))
        self.calendarSidePanel.pack_propagate(False)

        self.createCalendarEventButton = Button(
            self.calendarSidePanel,
            text="+ Create",
            command=self._toggleCalendarEventComposer,
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            activeforeground="#08111d",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 11),
            padx=16,
            pady=10,
            cursor="hand2",
        )
        self.createCalendarEventButton.pack(anchor="w", padx=14, pady=(14, 12))

        self.calendarMiniMonthFrame = Frame(self.calendarSidePanel, bg=TRANSCRIPT_BG)
        self.calendarMiniMonthFrame.pack(fill=X, padx=12, pady=(0, 14))

        self.calendarSideSearchFrame = Frame(self.calendarSidePanel, bg=TRANSCRIPT_BG)
        self.calendarSideSearchFrame.pack(fill=X, padx=12, pady=(0, 12))

        Label(
            self.calendarSidePanel,
            text="My calendars",
            bg=TRANSCRIPT_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", padx=14, pady=(4, 6))

        self.calendarSideActionsFrame = Frame(self.calendarSidePanel, bg=TRANSCRIPT_BG)
        self.calendarSideActionsFrame.pack(fill=X, padx=12, pady=(0, 12))

        self.calendarMainPanel = Frame(self.calendarBodyFrame, bg=PANEL_BG)
        self.calendarMainPanel.pack(side=LEFT, fill=BOTH, expand=True)

        self.calendarSummaryLabel = Label(
            self.calendarMainPanel,
            text="",
            bg=PANEL_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 12),
        )
        self.calendarSummaryLabel.pack(anchor="w", pady=(0, 12))

        self.calendarItemsFrame = Frame(self.calendarMainPanel, bg=PANEL_BG)
        self.calendarItemsFrame.pack(fill=BOTH, expand=True)

        self.calendarEmptyLabel = Label(
            self.calendarItemsFrame,
            text="No events, tasks, or reminders for this day.",
            bg=PANEL_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.calendarEmptyLabel.pack(padx=18, pady=24)
        self._buildCalendarToolsPanel(self.calendarSidePanel)
        self._syncCalendarDayEntry()

    def _buildCalendarToolsPanel(self, container):
        """Build Google/Apple inspired calendar management controls."""

        self._renderCalendarMiniMonth()

        tools = Frame(container, bg=TRANSCRIPT_BG)
        tools.pack(fill=X, padx=12, pady=(0, 12))

        self.calendarToolEntries = {}

        search_bar = Frame(
            self.calendarSideSearchFrame,
            bg=TRANSCRIPT_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        search_bar.pack(fill=X)
        Label(
            search_bar,
            text="Search",
            bg=TRANSCRIPT_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI Semibold", 9),
        ).pack(side=LEFT, padx=(10, 8), pady=8)
        self.calendarToolEntries["query"] = Entry(
            search_bar,
            bg=TRANSCRIPT_BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11),
        )
        self.calendarToolEntries["query"].pack(side=LEFT, fill=X, expand=True, ipady=6)
        self.calendarToolEntries["query"].bind("<Return>", lambda _event: self._searchCalendarFromTools())
        Button(
            search_bar,
            text="Go",
            command=self._searchCalendarFromTools,
            bg=ACCENT,
            fg="#08111d",
            activebackground=ACCENT_ACTIVE,
            activeforeground="#08111d",
            relief="flat",
            bd=0,
            font=("Segoe UI Semibold", 9),
            padx=12,
            pady=7,
            cursor="hand2",
        ).pack(side=LEFT, padx=8, pady=6)

        quick_actions = Frame(self.calendarSideActionsFrame, bg=TRANSCRIPT_BG)
        quick_actions.pack(fill=X, pady=(0, 8))
        quick_action_specs = [
            ("Events", self._createCalendarEventFromTools, NAV_INACTIVE, TEXT_PRIMARY),
            ("Tasks", self._createCalendarTaskFromTools, NAV_INACTIVE, TEXT_PRIMARY),
            ("Reminders", self._createCalendarReminderFromTools, NAV_INACTIVE, TEXT_PRIMARY),
            ("Calendars", self._listCalendarsFromTools, NAV_INACTIVE, TEXT_PRIMARY),
            ("Conflicts", self._checkCalendarConflictsFromTools, NAV_INACTIVE, TEXT_PRIMARY),
            ("Clear", self._clearCalendarSearch, NAV_INACTIVE, TEXT_PRIMARY),
        ]
        for label_text, command, background, foreground in quick_action_specs:
            Button(
                quick_actions,
                text=label_text,
                command=command,
                bg=background,
                fg=foreground,
                activebackground=ACCENT_ACTIVE if background == ACCENT else NAV_INACTIVE_ACTIVE,
                activeforeground=foreground,
                relief="flat",
                bd=0,
                font=("Segoe UI Semibold", 9),
                padx=10,
                pady=7,
                cursor="hand2",
            ).pack(fill=X, pady=(0, 5))

        details = Frame(
            tools,
            bg=TRANSCRIPT_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        details.pack(fill=X, pady=(4, 8))
        Label(
            details,
            text="Quick edit",
            bg=TRANSCRIPT_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", padx=10, pady=(8, 4))

        field_groups = [
            [
                ("title", "Title"),
                ("date", "Date"),
                ("start", "Start"),
                ("end", "End/Due"),
            ],
            [
                ("description", "Notes"),
                ("location", "Location"),
                ("attendees", "People"),
                ("calendar_id", "Calendar"),
            ],
            [
                ("item_id", "Item ID"),
                ("scope", "Scope"),
                ("occurrence", "Occurrence"),
                ("priority", "Priority/Kind"),
            ],
            [
                ("recurrence_type", "Repeats"),
                ("recurrence_interval", "Every"),
                ("recurrence_until", "Until"),
                ("recurrence_count", "Count"),
            ],
            [
                ("status", "Status"),
                ("timezone", "Timezone"),
                ("categories", "Categories"),
                ("organizer", "Organizer"),
                ("visibility", "Visibility"),
            ],
            [
                ("all_day", "All Day"),
                ("notification_preferences", "Notify JSON"),
                ("event_id", "Event ID"),
                ("task_id", "Task ID"),
            ],
        ]

        for group in field_groups:
            row_frame = Frame(details, bg=TRANSCRIPT_BG)
            row_frame.pack(fill=X, padx=10, pady=(0, 6))
            for key, label_text in group:
                field = Frame(row_frame, bg=TRANSCRIPT_BG)
                field.pack(fill=X, pady=(0, 4))
                Label(
                    field,
                    text=label_text,
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_MUTED,
                    font=("Segoe UI", 8),
                ).pack(anchor="w")
                entry = Entry(
                    field,
                    bg=INPUT_BG,
                    fg=TEXT_PRIMARY,
                    insertbackground=TEXT_PRIMARY,
                    relief="flat",
                    bd=0,
                    font=("Segoe UI", 9),
                )
                entry.pack(fill=X, ipady=5)
                self.calendarToolEntries[key] = entry

        management_rows = [
            [
                ("Update Event", self._updateCalendarEventFromTools),
                ("Delete Event", self._deleteCalendarEventFromTools),
            ],
            [
                ("Update Task", self._updateCalendarTaskFromTools),
                ("Delete Task", self._deleteCalendarTaskFromTools),
            ],
            [
                ("Update Reminder", self._updateCalendarReminderFromTools),
                ("Delete Reminder", self._deleteCalendarReminderFromTools),
            ],
            [
                ("List Calendars", self._listCalendarsFromTools),
                ("Select Calendar", self._selectCalendarFromTools),
            ],
            [
                ("Update Occurrence", self._updateCalendarOccurrenceFromTools),
                ("Cancel Occurrence", self._cancelCalendarOccurrenceFromTools),
                ("Update Series", self._updateCalendarSeriesFromTools),
                ("Delete Series", self._deleteCalendarSeriesFromTools),
            ],
        ]

        for row in management_rows:
            action_row = Frame(tools, bg=PANEL_BG)
            action_row.pack(fill=X, pady=(2, 4))
            for label_text, command in row:
                Button(
                    action_row,
                    text=label_text,
                    command=command,
                    bg=NAV_INACTIVE,
                    fg=TEXT_PRIMARY,
                    activebackground=NAV_INACTIVE_ACTIVE,
                    activeforeground=TEXT_PRIMARY,
                    relief="flat",
                    bd=0,
                font=("Segoe UI Semibold", 9),
                padx=8,
                pady=6,
                cursor="hand2",
                ).pack(side=LEFT, padx=(0, 6))

    def _renderCalendarMiniMonth(self):
        """Render a compact mini month in the calendar sidebar."""

        if not hasattr(self, "calendarMiniMonthFrame"):
            return

        for child in list(getattr(self.calendarMiniMonthFrame, "children", {}).values()):
            child.destroy()

        Label(
            self.calendarMiniMonthFrame,
            text=self.selectedCalendarDay.strftime("%B %Y"),
            bg=TRANSCRIPT_BG,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w", pady=(0, 6))

        days = Frame(self.calendarMiniMonthFrame, bg=TRANSCRIPT_BG)
        days.pack(fill=X)
        for label_text in ("M", "T", "W", "T", "F", "S", "S"):
            Label(
                days,
                text=label_text,
                bg=TRANSCRIPT_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI", 8),
                width=3,
            ).pack(side=LEFT)

        month_start = self.selectedCalendarDay.replace(day=1)
        grid_start = month_start - timedelta(days=month_start.weekday())
        for week_index in range(6):
            row = Frame(self.calendarMiniMonthFrame, bg=TRANSCRIPT_BG)
            row.pack(fill=X)
            for day_index in range(7):
                day_value = grid_start + timedelta(days=(week_index * 7) + day_index)
                is_selected = day_value == self.selectedCalendarDay
                is_other_month = day_value.month != self.selectedCalendarDay.month
                Label(
                    row,
                    text=str(day_value.day),
                    bg=ACCENT if is_selected else TRANSCRIPT_BG,
                    fg="#08111d" if is_selected else (TEXT_MUTED if is_other_month else TEXT_PRIMARY),
                    font=("Segoe UI Semibold" if is_selected else "Segoe UI", 8),
                    width=3,
                ).pack(side=LEFT, pady=1)

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

        self.calendarSearchActive = False
        self.activeCalendarView = view_name
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _showPreviousCalendarRange(self):
        """Move the selected calendar date back by the active view size."""

        self.calendarSearchActive = False
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

        self.calendarSearchActive = False
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

        self.calendarSearchActive = False
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

        self.calendarSearchActive = False
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _refreshCalendarView(self):
        """Reload calendar data for the active view and repaint the list."""

        self._setActiveCalendarViewButton()

        if self.calendarSearchActive:
            self._searchCalendarFromTools()
            return

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

        self._renderCalendarViewData(view_data, self._buildCalendarSummary(view_data))

    def _calendarService(self):
        """Return the calendar backend or raise a clear error."""

        return self.context.require("calendar")

    def _calendarToolValue(self, key: str) -> str:
        """Return one trimmed calendar tool field value."""

        entry = self.calendarToolEntries.get(key)
        if entry is None:
            return ""
        return entry.get().strip()

    def _calendarOptionalInt(self, key: str):
        """Parse an optional integer tool value."""

        value = self._calendarToolValue(key)
        if not value:
            return None
        return int(value)

    def _calendarCsv(self, key: str):
        """Parse a comma-separated tool field."""

        value = self._calendarToolValue(key)
        if not value:
            return None
        return [item.strip() for item in value.split(",") if item.strip()]

    def _calendarBool(self, key: str):
        """Parse an optional boolean tool field."""

        value = self._calendarToolValue(key).lower()
        if not value:
            return None
        return value in {"1", "true", "yes", "y", "on"}

    def _calendarJson(self, key: str):
        """Parse an optional JSON tool field."""

        value = self._calendarToolValue(key)
        if not value:
            return None
        return json.loads(value)

    def _calendarDateTimeFromTools(self, date_key: str = "date", time_key: str = "start"):
        """Build a datetime string from date and time tool fields."""

        date_value = self._calendarToolValue(date_key)
        time_value = self._calendarToolValue(time_key)
        if not date_value and not time_value:
            return None
        if not date_value:
            date_value = self.selectedCalendarDay.strftime("%Y-%m-%d")
        if not time_value:
            return date_value
        return f"{date_value} {time_value}"

    def _calendarRecurrenceFields(self):
        """Collect recurrence fields shared by events, tasks, and reminders."""

        fields = {}
        recurrence_type = self._calendarToolValue("recurrence_type")
        recurrence_interval = self._calendarToolValue("recurrence_interval")
        recurrence_until = self._calendarToolValue("recurrence_until")
        recurrence_count = self._calendarToolValue("recurrence_count")

        if recurrence_type:
            fields["recurrence_type"] = recurrence_type
        if recurrence_interval:
            fields["recurrence_interval"] = int(recurrence_interval)
        if recurrence_until:
            fields["recurrence_until"] = recurrence_until
        if recurrence_count:
            fields["recurrence_count"] = int(recurrence_count)
        return fields

    def _calendarCommonFields(self):
        """Collect optional fields shared by calendar items."""

        fields = {}
        calendar_id = self._calendarOptionalInt("calendar_id")
        timezone = self._calendarToolValue("timezone")
        categories = self._calendarCsv("categories")
        status = self._calendarToolValue("status")
        notification_preferences = self._calendarJson("notification_preferences")

        if calendar_id is not None:
            fields["calendar_id"] = calendar_id
        elif self.selectedCalendarId is not None:
            fields["calendar_id"] = self.selectedCalendarId
        if timezone:
            fields["timezone"] = timezone
        if categories:
            fields["categories"] = categories
        if status:
            fields["status"] = status
        if notification_preferences is not None:
            fields["notification_preferences"] = notification_preferences
        fields.update(self._calendarRecurrenceFields())
        return fields

    def _createCalendarEventFromTools(self):
        """Create an event using the calendar tools panel."""

        title = self._calendarToolValue("title")
        start_at = self._calendarDateTimeFromTools("date", "start")
        if not title or not start_at:
            self._showErrorPopup("Event title, date, and start time are required.")
            return

        fields = self._calendarCommonFields()
        fields.update(
            {
                "title": title,
                "start_at": start_at,
                "description": self._calendarToolValue("description") or None,
                "location": self._calendarToolValue("location") or None,
                "attendees": self._calendarCsv("attendees"),
                "end_at": self._calendarDateTimeFromTools("date", "end"),
                "organizer": self._calendarToolValue("organizer") or None,
                "visibility": self._calendarToolValue("visibility") or "private",
            }
        )
        all_day = self._calendarBool("all_day")
        if all_day is not None:
            fields["all_day"] = all_day

        try:
            self._calendarService().createEvent(**fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _updateCalendarEventFromTools(self):
        """Update an event using the calendar tools panel."""

        event_id = self._calendarOptionalInt("item_id")
        if event_id is None:
            self._showErrorPopup("Event item ID is required.")
            return

        fields = self._calendarCommonFields()
        field_map = {
            "title": "title",
            "description": "description",
            "location": "location",
            "timezone": "timezone",
            "visibility": "visibility",
            "organizer": "organizer",
            "status": "status",
        }
        for source, target in field_map.items():
            value = self._calendarToolValue(source)
            if value:
                fields[target] = value
        attendees = self._calendarCsv("attendees")
        if attendees:
            fields["attendees"] = attendees
        start_at = self._calendarDateTimeFromTools("date", "start")
        end_at = self._calendarDateTimeFromTools("date", "end")
        if start_at:
            fields["start_at"] = start_at
        if end_at:
            fields["end_at"] = end_at
        all_day = self._calendarBool("all_day")
        if all_day is not None:
            fields["all_day"] = all_day

        try:
            self._calendarService().updateEvent(event_id, **fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _deleteCalendarEventFromTools(self):
        """Delete an event using the calendar tools panel."""

        event_id = self._calendarOptionalInt("item_id")
        if event_id is None:
            self._showErrorPopup("Event item ID is required.")
            return
        try:
            self._calendarService().deleteEvent(event_id)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _createCalendarTaskFromTools(self):
        """Create a calendar task using the tools panel."""

        title = self._calendarToolValue("title")
        if not title:
            self._showErrorPopup("Task title is required.")
            return

        fields = self._calendarCommonFields()
        fields.update(
            {
                "title": title,
                "description": self._calendarToolValue("description") or None,
                "due_at": self._calendarDateTimeFromTools("date", "end"),
                "priority": self._calendarToolValue("priority") or "normal",
                "linked_event_id": self._calendarOptionalInt("event_id"),
            }
        )

        try:
            self._calendarService().createTask(**fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _updateCalendarTaskFromTools(self):
        """Update a calendar task using the tools panel."""

        task_id = self._calendarOptionalInt("item_id")
        if task_id is None:
            self._showErrorPopup("Task item ID is required.")
            return

        fields = self._calendarCommonFields()
        for key in ("title", "description", "priority", "status", "timezone"):
            value = self._calendarToolValue(key)
            if value:
                fields[key] = value
        due_at = self._calendarDateTimeFromTools("date", "end")
        if due_at:
            fields["due_at"] = due_at

        try:
            self._calendarService().updateTask(task_id, **fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _deleteCalendarTaskFromTools(self):
        """Delete a calendar task using the tools panel."""

        task_id = self._calendarOptionalInt("item_id")
        if task_id is None:
            self._showErrorPopup("Task item ID is required.")
            return
        try:
            self._calendarService().deleteTask(task_id)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _createCalendarReminderFromTools(self):
        """Create a calendar reminder using the tools panel."""

        title = self._calendarToolValue("title")
        remind_at = self._calendarDateTimeFromTools("date", "start")
        if not title or not remind_at:
            self._showErrorPopup("Reminder title, date, and start time are required.")
            return

        fields = self._calendarCommonFields()
        fields.update(
            {
                "title": title,
                "notes": self._calendarToolValue("description") or None,
                "remind_at": remind_at,
                "event_id": self._calendarOptionalInt("event_id"),
                "task_id": self._calendarOptionalInt("task_id"),
            }
        )
        fields.pop("status", None)
        fields.pop("categories", None)

        try:
            self._calendarService().createReminder(**fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _updateCalendarReminderFromTools(self):
        """Update a calendar reminder using the tools panel."""

        reminder_id = self._calendarOptionalInt("item_id")
        if reminder_id is None:
            self._showErrorPopup("Reminder item ID is required.")
            return

        fields = self._calendarCommonFields()
        fields.pop("status", None)
        fields.pop("categories", None)
        for source, target in (("title", "title"), ("description", "notes"), ("timezone", "timezone")):
            value = self._calendarToolValue(source)
            if value:
                fields[target] = value
        remind_at = self._calendarDateTimeFromTools("date", "start")
        if remind_at:
            fields["remind_at"] = remind_at

        try:
            self._calendarService().updateReminder(reminder_id, **fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _deleteCalendarReminderFromTools(self):
        """Delete a calendar reminder using the tools panel."""

        reminder_id = self._calendarOptionalInt("item_id")
        if reminder_id is None:
            self._showErrorPopup("Reminder item ID is required.")
            return
        try:
            self._calendarService().deleteReminder(reminder_id)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _createCalendarFromTools(self):
        """Create a calendar container from the tools panel."""

        name = self._calendarToolValue("title")
        if not name:
            self._showErrorPopup("Calendar title is required.")
            return

        try:
            self._calendarService().createCalendar(
                name=name,
                description=self._calendarToolValue("description") or None,
                color=self._calendarToolValue("location") or None,
                timezone=self._calendarToolValue("timezone") or "UTC",
            )
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._listCalendarsFromTools()

    def _listCalendarsFromTools(self):
        """Render available calendar containers."""

        try:
            rows = self._calendarService().listCalendars()
        except Exception as error:
            self._showErrorPopup(str(error))
            return

        section_rows = []
        for row in rows:
            calendar_row = dict(row)
            section_rows.append(
                {
                    "kind": "Calendar",
                    "title": str(calendar_row.get("name") or "Untitled calendar"),
                    "when": f"ID {calendar_row.get('id')} - {calendar_row.get('timezone', 'UTC')}",
                    "sort_key": str(calendar_row.get("name") or ""),
                    "detail": str(calendar_row.get("description") or ""),
                    "row": calendar_row,
                }
            )
        self._renderCalendarSections(
            [{"title": "Calendars", "rows": section_rows}],
            f"{len(section_rows)} calendars",
        )

    def _selectCalendarFromTools(self):
        """Select the active calendar ID for calendar views and tools."""

        calendar_id = self._calendarOptionalInt("calendar_id") or self._calendarOptionalInt("item_id")
        if calendar_id is None:
            self._showErrorPopup("Calendar ID is required.")
            return

        self.selectedCalendarId = calendar_id
        self.calendarSearchActive = False
        self._refreshCalendarView()

    def _searchCalendarFromTools(self):
        """Search events, tasks, and reminders from the tools panel."""

        query = self._calendarToolValue("query")
        start_at = self._calendarDateTimeFromTools("date", "start")
        end_at = self._calendarDateTimeFromTools("date", "end")
        calendar_id = self._calendarOptionalInt("calendar_id") or self.selectedCalendarId

        try:
            calendar_service = self._calendarService()
            events = calendar_service.searchEvents(
                query=query or None,
                calendar_id=calendar_id,
                start_at=start_at,
                end_at=end_at,
                status=self._calendarToolValue("status") or None,
                location=self._calendarToolValue("location") or None,
                attendee=self._calendarToolValue("attendees") or None,
                all_day=self._calendarBool("all_day"),
            )
            tasks = calendar_service.searchTasks(
                query=query or None,
                calendar_id=calendar_id,
                status=self._calendarToolValue("status") or None,
                priority=self._calendarToolValue("priority") or None,
                due_after=start_at,
                due_before=end_at,
            )
            reminders = calendar_service.searchReminders(
                query=query or None,
                calendar_id=calendar_id,
                remind_after=start_at,
                remind_before=end_at,
            )
        except Exception as error:
            self._showErrorPopup(str(error))
            return

        self.calendarSearchActive = True
        view_data = {"events": events, "tasks": tasks, "reminders": reminders}
        sections = self._buildCalendarSections(view_data)
        summary = f"Search - {len(events)} events, {len(tasks)} tasks, {len(reminders)} reminders"
        self._renderCalendarSections(sections, summary)

    def _clearCalendarSearch(self):
        """Return from search results to the active calendar view."""

        self.calendarSearchActive = False
        self._refreshCalendarView()

    def _checkCalendarConflictsFromTools(self):
        """Render event conflicts for the requested time window."""

        start_at = self._calendarDateTimeFromTools("date", "start")
        end_at = self._calendarDateTimeFromTools("date", "end")
        if not start_at or not end_at:
            self._showErrorPopup("Conflict checks require date, start, and end.")
            return

        try:
            rows = self._calendarService().detectConflicts(
                start_at=start_at,
                end_at=end_at,
                calendar_id=self._calendarOptionalInt("calendar_id") or self.selectedCalendarId,
                exclude_event_id=self._calendarOptionalInt("item_id"),
            )
        except Exception as error:
            self._showErrorPopup(str(error))
            return

        section = {"title": "Conflicts", "rows": self._calendarRowsForKind("Event", rows)}
        self._renderCalendarSections([section], f"{len(rows)} conflicts")

    def _calendarTargetKind(self):
        """Infer the target item kind for recurrence/series operations."""

        value = self._calendarToolValue("priority").lower()
        if value in {"event", "task", "reminder"}:
            return value

        if self._calendarToolValue("task_id"):
            return "reminder"
        if self._calendarToolValue("event_id"):
            return "reminder"
        if self._calendarToolValue("end") and not self._calendarToolValue("start"):
            return "task"
        return "event"

    def _calendarSeriesFields(self, kind: str):
        """Collect fields for occurrence and series updates."""

        fields = self._calendarCommonFields()
        title = self._calendarToolValue("title")
        description = self._calendarToolValue("description")
        if title:
            fields["title"] = title
        if description:
            fields["notes" if kind == "reminder" else "description"] = description

        if kind == "event":
            start_at = self._calendarDateTimeFromTools("date", "start")
            end_at = self._calendarDateTimeFromTools("date", "end")
            if start_at:
                fields["start_at"] = start_at
            if end_at:
                fields["end_at"] = end_at
            location = self._calendarToolValue("location")
            if location:
                fields["location"] = location
            attendees = self._calendarCsv("attendees")
            if attendees:
                fields["attendees"] = attendees
            for key in ("organizer", "visibility"):
                value = self._calendarToolValue(key)
                if value:
                    fields[key] = value
            all_day = self._calendarBool("all_day")
            if all_day is not None:
                fields["all_day"] = all_day
        elif kind == "task":
            due_at = self._calendarDateTimeFromTools("date", "end")
            if due_at:
                fields["due_at"] = due_at
            priority = self._calendarToolValue("priority")
            if priority and priority.lower() not in {"event", "task", "reminder"}:
                fields["priority"] = priority
        else:
            remind_at = self._calendarDateTimeFromTools("date", "start")
            if remind_at:
                fields["remind_at"] = remind_at
            fields.pop("status", None)
            fields.pop("categories", None)

        return fields

    def _updateCalendarOccurrenceFromTools(self):
        """Override one recurring event, task, or reminder occurrence."""

        item_id = self._calendarOptionalInt("item_id")
        occurrence = self._calendarToolValue("occurrence")
        if item_id is None or not occurrence:
            self._showErrorPopup("Item ID and occurrence are required.")
            return

        kind = self._calendarTargetKind()
        fields = self._calendarSeriesFields(kind)
        try:
            service = self._calendarService()
            if kind == "task":
                service.updateTaskOccurrence(item_id, occurrence, **fields)
            elif kind == "reminder":
                service.updateReminderOccurrence(item_id, occurrence, **fields)
            else:
                service.updateOccurrence(item_id, occurrence, **fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _cancelCalendarOccurrenceFromTools(self):
        """Cancel one recurring event, task, or reminder occurrence."""

        item_id = self._calendarOptionalInt("item_id")
        occurrence = self._calendarToolValue("occurrence")
        if item_id is None or not occurrence:
            self._showErrorPopup("Item ID and occurrence are required.")
            return

        kind = self._calendarTargetKind()
        try:
            service = self._calendarService()
            if kind == "task":
                service.cancelTaskOccurrence(item_id, occurrence)
            elif kind == "reminder":
                service.cancelReminderOccurrence(item_id, occurrence)
            else:
                service.cancelOccurrence(item_id, occurrence)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _updateCalendarSeriesFromTools(self):
        """Update a recurring event, task, or reminder series."""

        item_id = self._calendarOptionalInt("item_id")
        if item_id is None:
            self._showErrorPopup("Item ID is required.")
            return

        kind = self._calendarTargetKind()
        scope = self._calendarToolValue("scope") or "all"
        occurrence = self._calendarToolValue("occurrence") or None
        fields = self._calendarSeriesFields(kind)
        try:
            service = self._calendarService()
            if kind == "task":
                service.updateTaskSeries(item_id, scope=scope, occurrence_due_at=occurrence, **fields)
            elif kind == "reminder":
                service.updateReminderSeries(item_id, scope=scope, occurrence_remind_at=occurrence, **fields)
            else:
                service.updateEventSeries(item_id, scope=scope, occurrence_start=occurrence, **fields)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _deleteCalendarSeriesFromTools(self):
        """Delete a recurring event, task, or reminder series by scope."""

        item_id = self._calendarOptionalInt("item_id")
        if item_id is None:
            self._showErrorPopup("Item ID is required.")
            return

        kind = self._calendarTargetKind()
        scope = self._calendarToolValue("scope") or "all"
        occurrence = self._calendarToolValue("occurrence") or None
        try:
            service = self._calendarService()
            if kind == "task":
                service.deleteTaskSeries(item_id, scope=scope, occurrence_due_at=occurrence)
            elif kind == "reminder":
                service.deleteReminderSeries(item_id, scope=scope, occurrence_remind_at=occurrence)
            else:
                service.deleteEventSeries(item_id, scope=scope, occurrence_start=occurrence)
        except Exception as error:
            self._showErrorPopup(str(error))
            return
        self._refreshCalendarView()

    def _loadCalendarViewData(self, calendar_service):
        """Call the backend calendar method for the active view."""

        selected_day = self.selectedCalendarDay.strftime("%Y-%m-%d")

        if self.activeCalendarView == "day":
            return dict(calendar_service.buildDayView(selected_day, calendar_id=self.selectedCalendarId))
        if self.activeCalendarView == "week":
            return dict(calendar_service.buildWeekView(selected_day, calendar_id=self.selectedCalendarId))
        if self.activeCalendarView == "month":
            return dict(calendar_service.buildMonthView(selected_day, calendar_id=self.selectedCalendarId))

        months = []
        total_events = []
        total_tasks = []
        total_reminders = []
        for month_index in range(1, 13):
            month_day = date(self.selectedCalendarDay.year, month_index, 1).strftime("%Y-%m-%d")
            month_view = dict(calendar_service.buildMonthView(month_day, calendar_id=self.selectedCalendarId))
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

    def _renderCalendarViewData(self, view_data, summary_text: str):
        """Render the active calendar view using a calendar-like layout."""

        if self.activeCalendarView == "day":
            self._renderCalendarDayTimeline(view_data, summary_text)
            return
        if self.activeCalendarView == "week":
            self._renderCalendarWeekColumns(view_data, summary_text)
            return
        if self.activeCalendarView == "month":
            self._renderCalendarMonthGrid(view_data, summary_text)
            return
        if self.activeCalendarView == "year":
            self._renderCalendarYearGrid(view_data, summary_text)
            return

        self._renderCalendarSections(self._buildCalendarSections(view_data), summary_text)

    def _clearCalendarRenderedItems(self):
        """Destroy all rendered calendar widgets."""

        for item in self.renderedCalendarItems:
            item["container"].destroy()
        self.renderedCalendarItems = []

    def _allCalendarRows(self, view_data):
        """Return all event, task, and reminder rows normalized for display."""

        rows = (
            self._calendarRowsForKind("Event", view_data.get("events", []))
            + self._calendarRowsForKind("Task", view_data.get("tasks", []))
            + self._calendarRowsForKind("Reminder", view_data.get("reminders", []))
        )
        rows.sort(key=lambda row: (row["sort_key"], row["kind"], row["title"]))
        return rows

    def _renderCalendarDayTimeline(self, view_data, summary_text: str):
        """Render a Google Calendar style single-day timeline."""

        self._clearCalendarRenderedItems()
        self.calendarSummaryLabel.configure(text=summary_text)

        rows = self._allCalendarRows(view_data)
        if not rows:
            self.calendarEmptyLabel.pack(padx=18, pady=24)
            return

        self.calendarEmptyLabel.pack_forget()
        timeline = Frame(
            self.calendarItemsFrame,
            bg=TRANSCRIPT_BG,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        timeline.pack(fill=BOTH, expand=True)
        self.renderedCalendarItems.append({"row": {"surface": "day"}, "container": timeline})

        header = Frame(timeline, bg=TRANSCRIPT_BG)
        header.pack(fill=X, padx=12, pady=(10, 8))
        Label(
            header,
            text=self.selectedCalendarDay.strftime("%a %d"),
            bg=TRANSCRIPT_BG,
            fg=ACCENT,
            font=("Segoe UI Semibold", 15),
        ).pack(side=LEFT)
        Label(
            header,
            text="Day schedule",
            bg=TRANSCRIPT_BG,
            fg=TEXT_MUTED,
            font=("Segoe UI", 10),
        ).pack(side="right")

        buckets = {}
        unscheduled = []
        for row in rows:
            hour = self._calendarRowHour(row)
            if hour is None:
                unscheduled.append(row)
            else:
                buckets.setdefault(hour, []).append(row)

        for hour in range(6, 23):
            slot = Frame(timeline, bg=TRANSCRIPT_BG)
            slot.pack(fill=X, padx=12, pady=(0, 4))

            Label(
                slot,
                text=f"{hour:02d}:00",
                bg=TRANSCRIPT_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI", 9),
                width=7,
            ).pack(side=LEFT, anchor="n")

            slot_body = Frame(slot, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
            slot_body.pack(side=LEFT, fill=X, expand=True)

            hour_rows = buckets.get(hour, [])
            if not hour_rows:
                Label(
                    slot_body,
                    text="",
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_MUTED,
                    font=("Segoe UI", 9),
                ).pack(anchor="w", padx=8, pady=8)
                continue

            for row in hour_rows:
                self._renderCalendarCompactItem(slot_body, row)

        if unscheduled:
            unscheduled_frame = Frame(timeline, bg=TRANSCRIPT_BG)
            unscheduled_frame.pack(fill=X, padx=12, pady=(8, 12))
            Label(
                unscheduled_frame,
                text="Unscheduled",
                bg=TRANSCRIPT_BG,
                fg=TEXT_MUTED,
                font=("Segoe UI Semibold", 10),
            ).pack(anchor="w")
            for row in unscheduled:
                self._renderCalendarCompactItem(unscheduled_frame, row)

    def _renderCalendarWeekColumns(self, view_data, summary_text: str):
        """Render week view as seven day columns."""

        self._clearCalendarRenderedItems()
        self.calendarSummaryLabel.configure(text=summary_text)

        rows = self._allCalendarRows(view_data)
        if not rows:
            self.calendarEmptyLabel.pack(padx=18, pady=24)
            return

        self.calendarEmptyLabel.pack_forget()
        surface = Frame(self.calendarItemsFrame, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
        surface.pack(fill=BOTH, expand=True)
        self.renderedCalendarItems.append({"row": {"surface": "week"}, "container": surface})

        week_start = self.selectedCalendarDay - timedelta(days=self.selectedCalendarDay.weekday())
        for offset in range(7):
            day_value = week_start + timedelta(days=offset)
            column = Frame(surface, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
            column.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 4), pady=8)
            Label(
                column,
                text=day_value.strftime("%a %d"),
                bg=TRANSCRIPT_BG,
                fg=ACCENT if day_value == self.selectedCalendarDay else TEXT_PRIMARY,
                font=("Segoe UI Semibold", 10),
            ).pack(anchor="w", padx=8, pady=(8, 4))
            day_rows = [row for row in rows if self._calendarRowDate(row) == day_value]
            if not day_rows:
                Label(column, text="No items", bg=TRANSCRIPT_BG, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=8)
            for row in day_rows:
                self._renderCalendarCompactItem(column, row)

    def _renderCalendarMonthGrid(self, view_data, summary_text: str):
        """Render month view as a compact month grid."""

        self._clearCalendarRenderedItems()
        self.calendarSummaryLabel.configure(text=summary_text)

        rows = self._allCalendarRows(view_data)
        self.calendarEmptyLabel.pack_forget()
        surface = Frame(self.calendarItemsFrame, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
        surface.pack(fill=BOTH, expand=True)
        self.renderedCalendarItems.append({"row": {"surface": "month"}, "container": surface})

        month_start = self.selectedCalendarDay.replace(day=1)
        grid_start = month_start - timedelta(days=month_start.weekday())
        for week_index in range(6):
            week_row = Frame(surface, bg=TRANSCRIPT_BG)
            week_row.pack(fill=BOTH, expand=True, padx=8, pady=(8 if week_index == 0 else 0, 4))
            for day_index in range(7):
                day_value = grid_start + timedelta(days=(week_index * 7) + day_index)
                cell = Frame(week_row, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
                cell.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 4))
                muted = day_value.month != self.selectedCalendarDay.month
                Button(
                    cell,
                    text=str(day_value.day),
                    command=lambda selected_day=day_value: self._showCalendarDayFromMonth(selected_day),
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_MUTED if muted else TEXT_PRIMARY,
                    activebackground=NAV_INACTIVE_ACTIVE,
                    activeforeground=TEXT_PRIMARY,
                    relief="flat",
                    bd=0,
                    font=("Segoe UI Semibold", 9),
                    cursor="hand2",
                ).pack(anchor="w", padx=6, pady=(5, 2))
                for row in [item for item in rows if self._calendarRowDate(item) == day_value][:3]:
                    self._renderCalendarPill(cell, row)

    def _showCalendarDayFromMonth(self, day_value):
        """Open one day from the month view."""

        if not isinstance(day_value, date):
            return

        self.calendarSearchActive = False
        self.selectedCalendarDay = day_value
        self.activeCalendarView = "day"
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _renderCalendarYearGrid(self, view_data, summary_text: str):
        """Render year view as twelve month cards."""

        self._clearCalendarRenderedItems()
        self.calendarSummaryLabel.configure(text=summary_text)

        surface = Frame(self.calendarItemsFrame, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
        surface.pack(fill=BOTH, expand=True)
        self.calendarEmptyLabel.pack_forget()
        self.renderedCalendarItems.append({"row": {"surface": "year"}, "container": surface})

        months = view_data.get("months", [])
        for row_index in range(4):
            row_frame = Frame(surface, bg=TRANSCRIPT_BG)
            row_frame.pack(fill=BOTH, expand=True, padx=8, pady=(8 if row_index == 0 else 0, 4))
            for col_index in range(3):
                month_index = (row_index * 3) + col_index
                if month_index >= len(months):
                    continue
                month_view = months[month_index]
                month_rows = (
                    self._calendarRowsForKind("Event", month_view.get("events", []))
                    + self._calendarRowsForKind("Task", month_view.get("tasks", []))
                    + self._calendarRowsForKind("Reminder", month_view.get("reminders", []))
                )
                card = Frame(row_frame, bg=TRANSCRIPT_BG, highlightbackground=BORDER, highlightthickness=1, bd=0)
                card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 6))
                Button(
                    card,
                    text=self._formatMonthLabel(month_view.get("month")),
                    command=lambda selected_month=month_view.get("month"): self._showCalendarMonthFromYear(selected_month),
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_PRIMARY,
                    activebackground=NAV_INACTIVE_ACTIVE,
                    activeforeground=TEXT_PRIMARY,
                    relief="flat",
                    bd=0,
                    font=("Segoe UI Semibold", 10),
                    cursor="hand2",
                ).pack(anchor="w", padx=8, pady=(8, 4))
                Label(
                    card,
                    text=f"{len(month_rows)} items",
                    bg=TRANSCRIPT_BG,
                    fg=TEXT_MUTED,
                    font=("Segoe UI", 9),
                ).pack(anchor="w", padx=8, pady=(0, 8))

    def _showCalendarMonthFromYear(self, month_value):
        """Open one month from the year view."""

        try:
            selected_month = datetime.strptime(str(month_value), "%Y-%m").date()
        except ValueError:
            return

        self.calendarSearchActive = False
        self.selectedCalendarDay = selected_month.replace(day=1)
        self.activeCalendarView = "month"
        self._syncCalendarDayEntry()
        self._refreshCalendarView()

    def _renderCalendarCompactItem(self, parent, row):
        """Render one compact calendar item."""

        item = Frame(parent, bg=NAV_INACTIVE, highlightbackground=BORDER, highlightthickness=1, bd=0)
        item.pack(fill=X, padx=6, pady=(4, 4))
        Label(
            item,
            text=f"{row['when']}  {row['title']}",
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w", padx=8, pady=(6, 2))
        Label(
            item,
            text=row["kind"] if not row["detail"] else f"{row['kind']} - {row['detail']}",
            bg=NAV_INACTIVE,
            fg=TEXT_MUTED,
            font=("Segoe UI", 8),
            wraplength=480,
        ).pack(anchor="w", padx=8, pady=(0, 6))

    def _renderCalendarPill(self, parent, row):
        """Render one tiny month-grid pill."""

        Label(
            parent,
            text=f"{row['kind'][0]} {row['title']}",
            bg=NAV_INACTIVE,
            fg=TEXT_PRIMARY,
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill=X, padx=5, pady=(0, 3))

    def _calendarRowDate(self, row):
        """Return the date for a rendered calendar row."""

        raw_value = row.get("sort_key") or ""
        try:
            return datetime.strptime(str(raw_value)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    def _calendarRowHour(self, row):
        """Return the hour for a rendered calendar row."""

        raw_value = row.get("sort_key") or ""
        try:
            return datetime.strptime(str(raw_value)[:19], "%Y-%m-%d %H:%M:%S").hour
        except ValueError:
            try:
                return datetime.strptime(str(raw_value)[:16], "%Y-%m-%d %H:%M").hour
            except ValueError:
                return None

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
        self._renderCalendarMiniMonth()

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
