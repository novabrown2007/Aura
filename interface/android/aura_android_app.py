"""Kivy-based Android visual interface for Aura."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from interface.model_status import format_current_model_label

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.screenmanager import Screen, ScreenManager
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.textinput import TextInput
except ImportError:  # pragma: no cover - optional Android UI dependency
    App = None
    BoxLayout = None
    Button = None
    Label = None
    Screen = None
    ScreenManager = None
    ScrollView = None
    TextInput = None


class AuraAndroidApp:
    """
    Android visual shell that calls Aura backend services directly.

    Kivy is intentionally optional at import time so backend tests and desktop
    tooling do not need Android UI dependencies installed.
    """

    def __init__(self, context):
        """Store the runtime context used by the Android visual shell."""

        self.context = context
        self.logger = context.logger.getChild("AndroidApp") if context.logger else None
        self.selectedCalendarDay = date.today()
        self.selectedCalendarId = None
        self._kivyApp = None

    def run(self):
        """Start the Android UI."""

        if App is None:
            raise RuntimeError("Kivy is required to run the Android interface.")

        outer = self

        class _AuraKivyApp(App):
            """Small Kivy application wrapper around the Aura Android shell."""

            def build(self):
                return outer._buildRoot()

            def on_stop(self):
                outer.context.should_exit = True

        self._kivyApp = _AuraKivyApp()
        return self._kivyApp.run()

    def _buildRoot(self):
        """Build the root screen manager."""

        self.screenManager = ScreenManager()
        self.chatScreen = self._buildChatScreen()
        self.remindersScreen = self._buildRemindersScreen()
        self.calendarScreen = self._buildCalendarScreen()
        self.notificationsScreen = self._buildNotificationsScreen()
        self.homeAutomationScreen = self._buildHomeAutomationScreen()

        for screen in (
            self.chatScreen,
            self.remindersScreen,
            self.calendarScreen,
            self.notificationsScreen,
            self.homeAutomationScreen,
        ):
            self.screenManager.add_widget(screen)

        return self.screenManager

    def _nav(self):
        """Build shared navigation controls."""

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=48)
        for name, target in (
            ("Chat", "chat"),
            ("Reminders", "reminders"),
            ("Calendar", "calendar"),
            ("Alerts", "notifications"),
            ("Home", "home_automation"),
        ):
            row.add_widget(Button(text=name, on_release=lambda _btn, screen=target: self._showScreen(screen)))
        return row

    def _showScreen(self, name: str):
        """Switch screens and refresh data-backed views."""

        self.screenManager.current = name
        if name == "reminders":
            self._refreshReminders()
        elif name == "calendar":
            self._refreshCalendar()
        elif name == "notifications":
            self._refreshNotifications()
        elif name == "home_automation":
            self._refreshHomeAutomation()

    def _buildChatScreen(self):
        """Build chat screen."""

        screen = Screen(name="chat")
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(self._nav())

        self.currentModelLabel = Label(
            text=format_current_model_label(self.context),
            size_hint_y=None,
        )
        self.currentModelLabel.bind(texture_size=lambda label, size: setattr(label, "height", size[1]))
        self.currentModelLabel.bind(size=lambda label, size: setattr(label, "text_size", (size[0], None)))
        root.add_widget(self.currentModelLabel)

        self.chatTranscript = Label(text="Aura Android interface initialized.", size_hint_y=None)
        self.chatTranscript.bind(texture_size=lambda label, size: setattr(label, "height", size[1]))
        scroll = ScrollView()
        scroll.add_widget(self.chatTranscript)
        root.add_widget(scroll)

        composer = BoxLayout(orientation="horizontal", size_hint_y=None, height=52, spacing=8)
        self.chatInput = TextInput(multiline=False)
        composer.add_widget(self.chatInput)
        composer.add_widget(Button(text="Send", size_hint_x=None, width=96, on_release=lambda _btn: self._sendChat()))
        root.add_widget(composer)
        screen.add_widget(root)
        return screen

    def _sendChat(self):
        """Submit chat text through the backend interpreter/router."""

        user_input = self.chatInput.text.strip()
        if not user_input:
            return
        self.chatInput.text = ""
        self._appendChat("You", user_input)

        try:
            interpreter = self.context.require("interpreter")
            router = self.context.require("intentRouter")
            intent = interpreter.interpret(user_input)
            response = router.route(intent)
        except Exception as error:
            response = f"Error: {error}"

        self._appendChat("Aura", str(response))

    def _appendChat(self, speaker: str, message: str):
        """Append one chat transcript line."""

        existing = self.chatTranscript.text.strip()
        addition = f"{speaker}: {message}"
        self.chatTranscript.text = f"{existing}\n\n{addition}" if existing else addition

    def _buildRemindersScreen(self):
        """Build reminders screen."""

        screen = Screen(name="reminders")
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(self._nav())

        composer = BoxLayout(orientation="vertical", size_hint_y=None, height=176, spacing=6)
        self.reminderTitleInput = TextInput(hint_text="Title", multiline=False)
        self.reminderContentInput = TextInput(hint_text="Notes", multiline=False)
        self.reminderDateInput = TextInput(hint_text="Date, e.g. 24/03/2026", multiline=False)
        self.reminderTimeInput = TextInput(hint_text="Time, e.g. 17:00", multiline=False)
        composer.add_widget(self.reminderTitleInput)
        composer.add_widget(self.reminderContentInput)
        composer.add_widget(self.reminderDateInput)
        composer.add_widget(self.reminderTimeInput)
        composer.add_widget(Button(text="Create Reminder", on_release=lambda _btn: self._createReminder()))
        root.add_widget(composer)

        self.remindersList = Label(text="", size_hint_y=None)
        self.remindersList.bind(texture_size=lambda label, size: setattr(label, "height", size[1]))
        scroll = ScrollView()
        scroll.add_widget(self.remindersList)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    def _createReminder(self):
        """Create a reminder through the backend reminder service."""

        title = self.reminderTitleInput.text.strip()
        content = self.reminderContentInput.text.strip()
        day_value = self.reminderDateInput.text.strip()
        time_value = self.reminderTimeInput.text.strip()
        if not title or not day_value or not time_value:
            self.remindersList.text = "Reminder title, date, and time are required."
            return

        try:
            self.context.require("reminders").createReminder(
                title=title,
                content=content,
                module_of_origin="android",
                reminder_at=f"{time_value} {day_value}",
            )
        except Exception as error:
            self.remindersList.text = f"Error: {error}"
            return

        self.reminderTitleInput.text = ""
        self.reminderContentInput.text = ""
        self.reminderDateInput.text = ""
        self.reminderTimeInput.text = ""
        self._refreshReminders()

    def _refreshReminders(self):
        """Load reminders from the backend."""

        try:
            rows = self.context.require("reminders").listReminders()
        except Exception as error:
            self.remindersList.text = f"Error: {error}"
            return

        self.remindersList.text = self._formatRows(rows, empty="No reminders.")

    def _buildNotificationsScreen(self):
        """Build notifications screen."""

        screen = Screen(name="notifications")
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(self._nav())
        root.add_widget(Button(text="Refresh", size_hint_y=None, height=48, on_release=lambda _btn: self._refreshNotifications()))
        self.notificationsList = Label(text="", size_hint_y=None)
        self.notificationsList.bind(texture_size=lambda label, size: setattr(label, "height", size[1]))
        scroll = ScrollView()
        scroll.add_widget(self.notificationsList)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    def _refreshNotifications(self):
        """Load notifications from the backend."""

        try:
            rows = self.context.require("notifications").listNotifications()
        except Exception as error:
            self.notificationsList.text = f"Error: {error}"
            return

        self.notificationsList.text = self._formatRows(rows, empty="No notifications.")

    def _buildHomeAutomationScreen(self):
        """Build home automation screen."""

        screen = Screen(name="home_automation")
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(self._nav())

        actions = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=8)
        actions.add_widget(Button(text="Refresh", on_release=lambda _btn: self._refreshHomeAutomation()))
        actions.add_widget(Button(text="Bridge", on_release=lambda _btn: self._startHomeAutomationBridge()))
        actions.add_widget(Button(text="Hub", on_release=lambda _btn: self._startHomeAutomationHub()))
        root.add_widget(actions)

        self.homeAutomationList = Label(text="", size_hint_y=None)
        self.homeAutomationList.bind(texture_size=lambda label, size: setattr(label, "height", size[1]))
        scroll = ScrollView()
        scroll.add_widget(self.homeAutomationList)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    def _refreshHomeAutomation(self):
        """Load home automation state from the backend."""

        try:
            state = self.context.require("homeAutomation").refresh()
        except Exception as error:
            self.homeAutomationList.text = f"Error: {error}"
            return

        self.homeAutomationList.text = self._formatHomeAutomationState(state)

    def _startHomeAutomationBridge(self):
        """Request bridge service start."""

        try:
            response = self.context.require("homeAutomation").startBridge()
            self.homeAutomationList.text = f"Bridge start requested.\n{response}"
        except Exception as error:
            self.homeAutomationList.text = f"Error: {error}"

    def _startHomeAutomationHub(self):
        """Request hub service start."""

        try:
            response = self.context.require("homeAutomation").startHub()
            self.homeAutomationList.text = f"Hub start requested.\n{response}"
        except Exception as error:
            self.homeAutomationList.text = f"Error: {error}"

    def _buildCalendarScreen(self):
        """Build calendar screen."""

        screen = Screen(name="calendar")
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(self._nav())

        controls = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=8)
        controls.add_widget(Button(text="<", size_hint_x=None, width=56, on_release=lambda _btn: self._shiftCalendarDay(-1)))
        self.calendarDayInput = TextInput(text=self.selectedCalendarDay.strftime("%Y-%m-%d"), multiline=False)
        controls.add_widget(self.calendarDayInput)
        controls.add_widget(Button(text="Load", size_hint_x=None, width=88, on_release=lambda _btn: self._loadCalendarDay()))
        controls.add_widget(Button(text=">", size_hint_x=None, width=56, on_release=lambda _btn: self._shiftCalendarDay(1)))
        root.add_widget(controls)

        event_box = BoxLayout(orientation="vertical", size_hint_y=None, height=176, spacing=6)
        self.eventTitleInput = TextInput(hint_text="Event title", multiline=False)
        self.eventDescriptionInput = TextInput(hint_text="Description", multiline=False)
        self.eventStartInput = TextInput(hint_text="Start time, e.g. 09:00", multiline=False)
        self.eventEndInput = TextInput(hint_text="End time, e.g. 10:00", multiline=False)
        event_box.add_widget(self.eventTitleInput)
        event_box.add_widget(self.eventDescriptionInput)
        event_box.add_widget(self.eventStartInput)
        event_box.add_widget(self.eventEndInput)
        event_box.add_widget(Button(text="Create Event", on_release=lambda _btn: self._createCalendarEvent()))
        root.add_widget(event_box)

        self.calendarList = Label(text="", size_hint_y=None)
        self.calendarList.bind(texture_size=lambda label, size: setattr(label, "height", size[1]))
        scroll = ScrollView()
        scroll.add_widget(self.calendarList)
        root.add_widget(scroll)
        screen.add_widget(root)
        return screen

    def _loadCalendarDay(self):
        """Load a selected calendar day."""

        try:
            self.selectedCalendarDay = self._parseDate(self.calendarDayInput.text.strip())
        except ValueError as error:
            self.calendarList.text = str(error)
            return
        self._refreshCalendar()

    def _shiftCalendarDay(self, offset: int):
        """Move the selected day and refresh."""

        self.selectedCalendarDay = self.selectedCalendarDay + timedelta(days=offset)
        self.calendarDayInput.text = self.selectedCalendarDay.strftime("%Y-%m-%d")
        self._refreshCalendar()

    def _createCalendarEvent(self):
        """Create a calendar event through the backend."""

        title = self.eventTitleInput.text.strip()
        start_time = self.eventStartInput.text.strip()
        if not title or not start_time:
            self.calendarList.text = "Event title and start time are required."
            return

        day_value = self.selectedCalendarDay.strftime("%Y-%m-%d")
        try:
            self.context.require("calendar").createEvent(
                title=title,
                description=self.eventDescriptionInput.text.strip() or None,
                start_at=f"{day_value} {start_time}",
                end_at=f"{day_value} {self.eventEndInput.text.strip()}" if self.eventEndInput.text.strip() else None,
                calendar_id=self.selectedCalendarId,
            )
        except Exception as error:
            self.calendarList.text = f"Error: {error}"
            return

        self.eventTitleInput.text = ""
        self.eventDescriptionInput.text = ""
        self.eventStartInput.text = ""
        self.eventEndInput.text = ""
        self._refreshCalendar()

    def _refreshCalendar(self):
        """Load day-view calendar data from the backend."""

        day_value = self.selectedCalendarDay.strftime("%Y-%m-%d")
        try:
            calendar = self.context.require("calendar")
            day_view = calendar.buildDayView(day_value, calendar_id=self.selectedCalendarId)
        except Exception as error:
            self.calendarList.text = f"Error: {error}"
            return

        rows = []
        rows.extend({"kind": "Event", **row} for row in day_view.get("events", []))
        rows.extend({"kind": "Task", **row} for row in day_view.get("tasks", []))
        rows.extend({"kind": "Reminder", **row} for row in day_view.get("reminders", []))
        self.calendarList.text = self._formatRows(rows, empty="No calendar items.")

    @staticmethod
    def _parseDate(raw_value: str) -> date:
        """Parse a date from Android UI input."""

        for format_string in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(str(raw_value), format_string).date()
            except ValueError:
                continue
        raise ValueError("Invalid date. Use YYYY-MM-DD or DD/MM/YYYY.")

    @staticmethod
    def _formatRows(rows, empty: str) -> str:
        """Format backend rows for compact mobile display."""

        prepared = [AuraAndroidApp._rowToDict(row) for row in rows]
        if not prepared:
            return empty

        lines = []
        for row in prepared:
            title = row.get("title") or row.get("name") or "Untitled"
            kind = row.get("kind") or row.get("source_module") or "Item"
            when = (
                row.get("start_at")
                or row.get("due_at")
                or row.get("remind_at")
                or row.get("reminder_at")
                or row.get("notification_at")
                or ""
            )
            detail = row.get("description") or row.get("content") or row.get("notes") or ""
            lines.append(f"{kind}: {title}\n{when}\n{detail}".strip())
        return "\n\n".join(lines)

    @staticmethod
    def _formatHomeAutomationState(state) -> str:
        """Format home automation state for compact mobile display."""

        state_row = AuraAndroidApp._rowToDict(state)
        lines = [
            f"Bridge: {state_row.get('bridge_name', 'Unavailable')}",
            f"Connected: {'Yes' if state_row.get('connected') else 'No'}",
            f"Online devices: {state_row.get('online_devices', 0)}",
        ]
        if state_row.get("last_error"):
            lines.append(f"Error: {state_row['last_error']}")

        for title, key in (("Lights", "lights"), ("Cameras", "cameras"), ("Devices", "devices")):
            rows = [AuraAndroidApp._rowToDict(row) for row in state_row.get(key, [])]
            lines.append(f"\n{title}")
            if not rows:
                lines.append("None")
                continue
            for row in rows:
                name = row.get("name") or row.get("device_id") or "Unknown"
                detail = row.get("status") or row.get("category") or ""
                if row.get("category") == "light":
                    detail = (
                        f"{'On' if row.get('is_on') else 'Off'} "
                        f"{row.get('brightness', 0)}% color={row.get('color', 'white')}"
                    )
                lines.append(f"- {name}: {detail}")
        return "\n".join(lines)

    @staticmethod
    def _rowToDict(row):
        """Convert backend row-like values to dictionaries."""

        if hasattr(row, "__dataclass_fields__"):
            data = {key: getattr(row, key) for key in row.__dataclass_fields__}
            if hasattr(row, "online_devices"):
                data["online_devices"] = row.online_devices
            return data
        return dict(row)
