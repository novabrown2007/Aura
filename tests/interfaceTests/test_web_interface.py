"""Web interface tests."""

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
import unittest

from interface.web import AuraWebApp, createWebServer
from interface.web.aura_web_app import AuraWebRequestHandler
from scripts.interface_build import createBundlePlan
from tests.interfaceTests.helpers import makeInterfaceContext


class WebInterfaceTests(unittest.TestCase):
    """Tests that cover only the web interface package."""

    def setUp(self):
        self.context = makeInterfaceContext()
        self.handler = AuraWebRequestHandler.__new__(AuraWebRequestHandler)
        self.handler.aura_context = self.context
        self.handler.aura_app = SimpleNamespace(selectedCalendarId=None)

    def test_web_package_exports_app(self):
        self.assertEqual(AuraWebApp.__name__, "AuraWebApp")

    def test_web_build_plan_includes_only_web_interface(self):
        plan = createBundlePlan("web")
        self.assertIn("interface/web", plan.included_paths)
        self.assertNotIn("interface/windows", plan.included_paths)
        self.assertNotIn("interface/android", plan.included_paths)

    def test_web_build_files_exist(self):
        root = Path(__file__).resolve().parents[2]
        self.assertTrue((root / "interface" / "web" / "requirements.txt").is_file())
        self.assertTrue((root / "interface" / "web" / "build.py").is_file())

    def test_create_web_server_binds_with_ephemeral_port(self):
        server = createWebServer(self.context, host="127.0.0.1", port=0)
        try:
            self.assertGreater(server.server_address[1], 0)
        finally:
            server.server_close()

    def test_static_assets_exist(self):
        static_root = Path(__file__).resolve().parents[2] / "interface" / "web" / "static"
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
