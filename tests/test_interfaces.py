"""Regression tests for Aura visual interface packages."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
import unittest

from interface.android import aura_android_app as android_module
from interface.android import AuraAndroidApp
from interface.web import AuraWebApp, createWebServer
from interface.web.aura_web_app import AuraWebRequestHandler
from interface.windows import AuraWindowsApp
from tests.support.fakes import TestContext


class FakeInterpreter:
    """Minimal interpreter stub for chat route tests."""

    def interpret(self, message):
        return {"text": message}


class FakeRouter:
    """Minimal router stub for chat route tests."""

    def route(self, intent):
        return f"handled {intent['text']}"


class FakeReminders:
    """Reminder backend stub for web route tests."""

    def __init__(self):
        self.rows = [{"id": 1, "title": "Standup", "reminder_at": "2026-05-20 09:00:00"}]
        self.deleted = []

    def listReminders(self):
        return list(self.rows)

    def createReminder(self, title, content, module_of_origin, reminder_at=None):
        self.rows.append(
            {
                "id": 2,
                "title": title,
                "content": content,
                "module_of_origin": module_of_origin,
                "reminder_at": reminder_at,
            }
        )
        return 2

    def deleteReminder(self, reminder_id):
        self.deleted.append(reminder_id)


class FakeNotifications:
    """Notification backend stub for web route tests."""

    def __init__(self):
        self.deleted = []

    def listNotifications(self, status=None, limit=None):
        rows = [{"id": 4, "title": "Alert", "status": status or "pending"}]
        return rows[:limit] if limit else rows

    def deleteNotification(self, notification_id):
        self.deleted.append(notification_id)


class FakeCalendar:
    """Calendar backend stub for web route tests."""

    def __init__(self):
        self.created_events = []
        self.created_tasks = []
        self.created_reminders = []
        self.created_calendars = []

    def listCalendars(self):
        return [{"id": 7, "name": "Aura"}]

    def createCalendar(self, **fields):
        self.created_calendars.append(fields)

    def buildDayView(self, day, calendar_id=None):
        return {
            "day": day,
            "events": [{"id": 1, "title": "Event", "start_at": f"{day} 10:00:00"}],
            "tasks": [],
            "reminders": [],
        }

    def buildWeekView(self, day, calendar_id=None):
        return {"week_start": day, "week_end": day, "events": [], "tasks": [], "reminders": []}

    def buildMonthView(self, month_value, calendar_id=None):
        return {"month": str(month_value)[:7], "events": [], "tasks": [], "reminders": []}

    def _normalizeDateValue(self, value):
        return value

    def createEvent(self, **fields):
        self.created_events.append(fields)
        return 10

    def getEvent(self, event_id):
        return {"id": event_id}

    def updateEvent(self, event_id, **fields):
        self.updated_event = (event_id, fields)

    def deleteEvent(self, event_id):
        self.deleted_event = event_id

    def createTask(self, **fields):
        self.created_tasks.append(fields)
        return 20

    def getTask(self, task_id):
        return {"id": task_id}

    def updateTask(self, task_id, **fields):
        self.updated_task = (task_id, fields)

    def deleteTask(self, task_id):
        self.deleted_task = task_id

    def createReminder(self, **fields):
        self.created_reminders.append(fields)
        return 30

    def getReminder(self, reminder_id):
        return {"id": reminder_id}

    def updateReminder(self, reminder_id, **fields):
        self.updated_reminder = (reminder_id, fields)

    def deleteReminder(self, reminder_id):
        self.deleted_reminder = reminder_id

    def searchEvents(self, query=None, calendar_id=None):
        return [{"id": 1, "title": query or "Event"}]

    def searchTasks(self, query=None, calendar_id=None):
        return []

    def searchReminders(self, query=None, calendar_id=None):
        return []

    def detectConflicts(self, start_at, end_at, calendar_id=None, exclude_event_id=None):
        return [{"id": 1, "start_at": start_at, "end_at": end_at}]


def make_interface_context():
    """Build a context with enough backend services for interface tests."""

    context = TestContext()
    context.logger = None
    context.should_exit = False
    context.interpreter = FakeInterpreter()
    context.intentRouter = FakeRouter()
    context.reminders = FakeReminders()
    context.notifications = FakeNotifications()
    context.calendar = FakeCalendar()
    return context


class InterfaceImportTests(unittest.TestCase):
    """Smoke tests for import-safe interface packages."""

    def test_visual_interface_packages_export_apps(self):
        self.assertEqual(AuraWindowsApp.__name__, "AuraWindowsApp")
        self.assertEqual(AuraAndroidApp.__name__, "AuraAndroidApp")
        self.assertEqual(AuraWebApp.__name__, "AuraWebApp")

    def test_android_run_requires_kivy_when_dependency_is_missing(self):
        app = AuraAndroidApp(make_interface_context())
        if android_module.App is not None:
            self.skipTest("Kivy is installed in this environment.")
        with self.assertRaisesRegex(RuntimeError, "Kivy is required"):
            app.run()


class WebInterfaceTests(unittest.TestCase):
    """Tests for the stdlib web API wrapper around Aura backends."""

    def setUp(self):
        self.context = make_interface_context()
        self.handler = AuraWebRequestHandler.__new__(AuraWebRequestHandler)
        self.handler.aura_context = self.context
        self.handler.aura_app = SimpleNamespace(selectedCalendarId=None)

    def test_create_web_server_binds_with_ephemeral_port(self):
        server = createWebServer(self.context, host="127.0.0.1", port=0)
        try:
            self.assertGreater(server.server_address[1], 0)
        finally:
            server.server_close()

    def test_static_assets_exist(self):
        static_root = Path(__file__).resolve().parents[1] / "interface" / "web" / "static"
        for filename in ("index.html", "styles.css", "app.js"):
            self.assertTrue((static_root / filename).is_file(), filename)

    def test_chat_route_uses_interpreter_and_router(self):
        response = self.handler._dispatchApi(
            "POST",
            "/api/chat",
            {},
            {"message": "hello"},
        )
        self.assertEqual(response, {"response": "handled hello"})

    def test_reminder_routes_call_backend(self):
        rows = self.handler._dispatchApi("GET", "/api/reminders", {}, {})
        self.assertEqual(rows[0]["title"], "Standup")

        created = self.handler._dispatchApi(
            "POST",
            "/api/reminders",
            {},
            {"title": "Ship", "content": "Release", "reminder_at": "2026-05-20 12:00"},
        )
        self.assertEqual(created, {"id": 2})

        self.handler._dispatchApi("DELETE", "/api/reminders/2", {}, {})
        self.assertEqual(self.context.reminders.deleted, [2])

    def test_notification_routes_call_backend(self):
        rows = self.handler._dispatchApi("GET", "/api/notifications", {"limit": ["1"]}, {})
        self.assertEqual(rows[0]["status"], "pending")

        self.handler._dispatchApi("DELETE", "/api/notifications/4", {}, {})
        self.assertEqual(self.context.notifications.deleted, [4])

    def test_calendar_routes_call_backend(self):
        calendars = self.handler._dispatchApi("GET", "/api/calendar/calendars", {}, {})
        self.assertEqual(calendars["calendars"][0]["name"], "Aura")

        view = self.handler._dispatchApi(
            "GET",
            "/api/calendar/view",
            {"view": ["day"], "date": ["2026-05-20"]},
            {},
        )
        self.assertEqual(view["events"][0]["title"], "Event")

        event = self.handler._dispatchApi(
            "POST",
            "/api/calendar/events",
            {},
            {"title": "Planning", "start_at": "2026-05-20 10:00", "calendar_id": "7"},
        )
        self.assertEqual(event, {"id": 10})
        self.assertEqual(self.context.calendar.created_events[0]["calendar_id"], 7)

        task = self.handler._dispatchApi(
            "POST",
            "/api/calendar/tasks",
            {},
            {"title": "Follow up", "linked_event_id": "10"},
        )
        self.assertEqual(task, {"id": 20})
        self.assertEqual(self.context.calendar.created_tasks[0]["linked_event_id"], 10)

        reminder = self.handler._dispatchApi(
            "POST",
            "/api/calendar/reminders",
            {},
            {
                "title": "Leave",
                "remind_at": "2026-05-20 15:00",
                "linked_event_id": "10",
                "content": "Pack laptop",
            },
        )
        self.assertEqual(reminder, {"id": 30})
        self.assertEqual(self.context.calendar.created_reminders[0]["event_id"], 10)
        self.assertEqual(self.context.calendar.created_reminders[0]["notes"], "Pack laptop")

    def test_json_safe_formats_dates(self):
        value = self.handler._jsonSafe(
            {"today": date(2026, 5, 20), "stamp": datetime(2026, 5, 20, 12, 30)}
        )
        self.assertEqual(value, {"today": "2026-05-20", "stamp": "2026-05-20T12:30:00"})


if __name__ == "__main__":
    unittest.main()
