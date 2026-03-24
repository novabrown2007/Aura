"""Tests for Aura's CLI interface branch."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main
from core.interface.cliInterface import CliInterface
from modules.commands.commandHandler import CommandHandler
from tests.support.fakes import make_context


class _Logger:
    """Minimal logger stub with child support."""

    def getChild(self, _name):
        """Return self for child logger lookups."""

        return self

    def info(self, _message):
        """Accept info logs."""

        return None

    def close(self):
        """Accept logger close calls."""

        return None


class _CommandTestDatabase:
    """Database stub for command and CLI tests."""

    def __init__(self):
        """Initialize in-memory rows used by command tests."""

        self.memory = {}
        self.history = []

    def execute(self, query, params=()):
        """Handle memory and history writes."""

        normalized = " ".join(query.lower().split())
        if "insert into memory" in normalized:
            self.memory[params[0]] = params[1]
        elif normalized.startswith("delete from memory where memory_key"):
            self.memory.pop(params[0], None)
        elif normalized.startswith("delete from memory"):
            self.memory.clear()
        elif "insert into conversation_history" in normalized:
            self.history.append((params[0], params[1]))
        elif normalized.startswith("delete from conversation_history"):
            self.history.clear()
        return None

    def fetchOne(self, query, params=()):
        """Handle single-row memory lookups."""

        normalized = " ".join(query.lower().split())
        if "select value from memory where memory_key" in normalized:
            value = self.memory.get(params[0])
            return {"value": value} if value is not None else None
        return None

    def fetchAll(self, query, params=()):
        """Handle memory and history list queries."""

        normalized = " ".join(query.lower().split())
        if "select memory_key, value from memory" in normalized:
            return [{"memory_key": key, "value": value} for key, value in self.memory.items()]
        if "from conversation_history" in normalized:
            rows = [{"role": role, "content": content} for role, content in self.history]
            rows = list(reversed(rows))
            if params:
                rows = rows[: int(params[0])]
            return rows
        return []


class _CalendarStub:
    """Calendar backend stub that records CLI-facing operations."""

    def __init__(self):
        """Initialize in-memory calendar data for CLI tests."""

        self.created_events = []

    def listCalendars(self):
        """Return one fake calendar container."""

        return [{"id": 1, "name": "Default", "timezone": "America/Toronto"}]

    def buildDayView(self, day, calendar_id=None):
        """Return a fake day view payload."""

        return {"day": day, "calendar_id": calendar_id, "events": []}

    def buildWeekView(self, day, calendar_id=None):
        """Return a fake week view payload."""

        return {"anchor_day": day, "calendar_id": calendar_id, "days": []}

    def buildMonthView(self, month_value, calendar_id=None):
        """Return a fake month view payload."""

        return {"month": month_value, "calendar_id": calendar_id, "weeks": []}

    def createCalendar(self, **fields):
        """Return a fake created calendar identifier."""

        return 2

    def getCalendarTimezone(self, calendar_id=None):
        """Return the calendar timezone used by debug commands."""

        return "America/Toronto"

    def createEvent(self, **fields):
        """Record a created event and return its fake identifier."""

        self.created_events.append(fields)
        return len(self.created_events)

    def getEvent(self, event_id):
        """Return a fake event payload."""

        return {"id": event_id, "title": "Meeting"}

    def listEventsForRange(self, start_at, end_at, calendar_id=None):
        """Return a fake event range payload."""

        return [{"id": 1, "start_at": start_at, "end_at": end_at, "calendar_id": calendar_id}]

    def searchEvents(self, **fields):
        """Return a fake event search payload."""

        return [{"id": 1, "query": fields.get("query")}]

    def updateEvent(self, event_id, **fields):
        """Accept fake event updates."""

        return None

    def deleteEvent(self, event_id):
        """Accept fake event deletion."""

        return None

    def detectConflicts(self, **fields):
        """Return a fake overlap result."""

        return [{"id": 9, "title": "Conflict"}]

    def createTask(self, **fields):
        """Return a fake task identifier."""

        return 1

    def listTasks(self, calendar_id=None, status=None):
        """Return a fake task list."""

        return [{"id": 1, "calendar_id": calendar_id, "status": status or "pending"}]

    def searchTasks(self, **fields):
        """Return a fake task search payload."""

        return [{"id": 1, "query": fields.get("query")}]

    def getTask(self, task_id):
        """Return a fake task payload."""

        return {"id": task_id, "title": "Task"}

    def updateTask(self, task_id, **fields):
        """Accept fake task updates."""

        return None

    def deleteTask(self, task_id):
        """Accept fake task deletion."""

        return None

    def createReminder(self, **fields):
        """Return a fake reminder identifier."""

        return 1

    def listReminders(self, calendar_id=None, include_delivered=True):
        """Return a fake reminder list."""

        return [{"id": 1, "calendar_id": calendar_id, "include_delivered": include_delivered}]

    def searchReminders(self, **fields):
        """Return a fake reminder search payload."""

        return [{"id": 1, "query": fields.get("query")}]

    def getReminder(self, reminder_id):
        """Return a fake reminder payload."""

        return {"id": reminder_id, "title": "Reminder"}

    def updateReminder(self, reminder_id, **fields):
        """Accept fake reminder updates."""

        return None

    def deleteReminder(self, reminder_id):
        """Accept fake reminder deletion."""

        return None

    def processDueReminders(self):
        """Return a fake due-reminder processing result."""

        return [{"id": 1, "status": "processed"}]


class _SharedRemindersStub:
    """Shared reminder backend stub that records CLI-facing operations."""

    def __init__(self):
        """Initialize in-memory reminder rows for CLI tests."""

        self.rows = []
        self.next_id = 1

    def createReminder(self, title, content, module_of_origin, reminder_at=None):
        """Store a reminder row and return its fake identifier."""

        reminder = {
            "id": self.next_id,
            "title": title,
            "content": content,
            "module_of_origin": module_of_origin,
            "reminder_at": reminder_at,
        }
        self.rows.append(reminder)
        self.next_id += 1
        return reminder["id"]

    def getReminder(self, reminder_id):
        """Return one stored reminder row by ID."""

        for row in self.rows:
            if row["id"] == reminder_id:
                return dict(row)
        return None

    def listReminders(self):
        """Return all stored reminder rows."""

        return [dict(row) for row in self.rows]

    def deleteReminder(self, reminder_id):
        """Delete one stored reminder row by ID."""

        self.rows = [row for row in self.rows if row["id"] != reminder_id]


class _NotificationsStub:
    """Notifications backend stub that supports CLI debug inspection."""

    def __init__(self):
        """Initialize in-memory notification rows for CLI tests."""

        self.rows = [
            {
                "id": 1,
                "title": "Test notification",
                "content": "Hello",
                "notification_at": "2026-03-24 10:00:00",
                "source_module": "system",
                "status": "pending",
            }
        ]

    def listNotifications(self, status=None, limit=None):
        """Return notification rows with optional status and limit filtering."""

        rows = [dict(row) for row in self.rows]
        if status is not None:
            rows = [row for row in rows if row["status"] == status]
        if limit is not None:
            return rows[:limit]
        return rows

    def listDueNotifications(self, current_time=None):
        """Return fake due notifications."""

        return [dict(self.rows[0])]


class CliCommandTests(unittest.TestCase):
    """Validate command registration and execution against the current backend."""

    def _build_context(self):
        """Construct a runtime-like context for CLI command tests."""

        context = make_context(
            database=_CommandTestDatabase(),
            extra={
                "logger": _Logger(),
                "taskManager": SimpleNamespace(listTasks=lambda: ["schedule_alpha"]),
                "calendar": _CalendarStub(),
                "reminders": _SharedRemindersStub(),
                "notifications": _NotificationsStub(),
            },
        )
        context.system = SimpleNamespace(
            shutdown=lambda: setattr(context, "should_exit", True) or True,
            restart=lambda: setattr(context, "restart_requested", True) or setattr(context, "should_exit", True) or True,
            reload=lambda: {"database": {"host": "localhost"}},
        )
        context.conversationHistory = SimpleNamespace(
            getRecentMessages=lambda limit=15: [("user", "hello"), ("aura", "world")][:limit],
            clear=lambda: None,
        )
        context.memoryManager = SimpleNamespace(
            get=lambda key: {"name": "Nova"}.get(key),
            setMemory=lambda key, value, importance=1: context.database.memory.__setitem__(key, value),
            delete=lambda key: context.database.memory.pop(key, None),
            getMemory=lambda: dict(context.database.memory),
            clear=lambda: context.database.memory.clear(),
        )
        context.commandHandler = CommandHandler(context)
        context.commandRegistry = context.commandHandler.registry
        context.engine = SimpleNamespace(handleInput=lambda text, source="cli", metadata=None: {"response": f"llm:{text}"})
        return context

    def test_command_handler_executes_memory_and_system_commands(self):
        """Command handler should dispatch nested commands against backend modules."""

        context = self._build_context()

        result = context.commandHandler.handle("/memory set project Aura")
        self.assertTrue(result.success)
        self.assertEqual(context.database.memory["project"], "Aura")

        result = context.commandHandler.handle("/system tasks")
        self.assertTrue(result.success)
        self.assertIn("schedule_alpha", result.message)

    def test_command_handler_reports_unknown_commands(self):
        """Unknown commands should return a failed result instead of crashing."""

        context = self._build_context()
        result = context.commandHandler.handle("/nope")
        self.assertFalse(result.success)
        self.assertIn("Unknown command", result.message)

    def test_command_handler_executes_calendar_commands(self):
        """Calendar command package should dispatch against the calendar backend."""

        context = self._build_context()

        list_result = context.commandHandler.handle("/calendar list")
        self.assertTrue(list_result.success)
        self.assertIn("Default", list_result.message)

        create_result = context.commandHandler.handle(
            "/calendar event create title=Meeting start_at='10:00 24/03/2026' end_at='11:00 24/03/2026'"
        )
        self.assertTrue(create_result.success)
        self.assertEqual(context.calendar.created_events[0]["title"], "Meeting")

        day_result = context.commandHandler.handle("/calendar day day=24/03/2026")
        self.assertTrue(day_result.success)
        self.assertIn("24/03/2026", day_result.message)

    def test_command_handler_creates_lists_and_deletes_shared_reminders(self):
        """Reminder commands should operate on the shared reminders module."""

        context = self._build_context()

        create_result = context.commandHandler.handle(
            "/reminder create title='Take meds' content='After dinner' module=system remind_at='19:00 24/03/2026'"
        )
        self.assertTrue(create_result.success)
        self.assertEqual(context.reminders.rows[0]["title"], "Take meds")

        list_result = context.commandHandler.handle("/reminder list")
        self.assertTrue(list_result.success)
        self.assertIn("Take meds", list_result.message)

        delete_result = context.commandHandler.handle("/reminder delete id=1")
        self.assertTrue(delete_result.success)
        self.assertEqual(context.reminders.rows, [])

    def test_command_handler_exposes_low_level_module_debug_views(self):
        """Debug commands should expose calendar, reminders, and notifications state."""

        context = self._build_context()
        context.reminders.createReminder("Take meds", "After dinner", "system", "19:00 24/03/2026")

        calendar_result = context.commandHandler.handle("/debug calendar")
        self.assertTrue(calendar_result.success)
        self.assertIn("default_timezone: America/Toronto", calendar_result.message)

        reminders_result = context.commandHandler.handle("/debug reminders")
        self.assertTrue(reminders_result.success)
        self.assertIn("entries: 1", reminders_result.message)

        notifications_result = context.commandHandler.handle("/debug notifications")
        self.assertTrue(notifications_result.success)
        self.assertIn("due_now: 1", notifications_result.message)


class CliInterfaceTests(unittest.TestCase):
    """Validate the interactive CLI loop behavior."""

    def _build_context(self):
        """Construct a runtime-like context for CLI loop tests."""

        context = make_context(extra={"logger": _Logger()})
        context.system = SimpleNamespace(shutdown=lambda: setattr(context, "should_exit", True) or True)
        context.commandHandler = CommandHandler(context)
        context.commandRegistry = context.commandHandler.registry
        context.taskManager = SimpleNamespace(listTasks=lambda: [])
        context.calendar = _CalendarStub()
        context.reminders = _SharedRemindersStub()
        context.notifications = _NotificationsStub()
        context.conversationHistory = SimpleNamespace(
            getRecentMessages=lambda limit=15: [],
            clear=lambda: None,
        )
        context.memoryManager = SimpleNamespace(
            get=lambda key: None,
            setMemory=lambda key, value, importance=1: None,
            delete=lambda key: None,
            getMemory=lambda: {},
            clear=lambda: None,
        )
        context.engine = SimpleNamespace(handleInput=lambda text, source="cli", metadata=None: {"response": f"llm:{text}"})
        return context

    def test_cli_runs_commands_then_normal_chat(self):
        """CLI should route slash commands and plain text through different paths."""

        context = self._build_context()
        inputs = iter(["/version", "hello", "/system shutdown"])
        outputs = []
        cli = CliInterface(context, input_func=lambda _prompt: next(inputs), output_func=outputs.append)

        cli.run()

        self.assertIn("Aura CLI ready. Use /help for commands.", outputs[0])
        self.assertTrue(any("Aura CLI interface branch" in line for line in outputs))
        self.assertTrue(any("llm:hello" in line for line in outputs))
        self.assertTrue(context.should_exit)


class CliMainTests(unittest.TestCase):
    """Validate CLI branch main-loop integration."""

    def test_main_builds_cli_interface_instead_of_headless_engine_run(self):
        """Main should launch the CLI interface on this branch."""

        context = SimpleNamespace(
            logger=SimpleNamespace(close=lambda: None),
            restart_requested=False,
        )

        with patch.object(main, "buildRuntimeContext", return_value=context), \
                patch.object(main, "startup") as startup_runtime, \
                patch.object(main, "shutdown") as shutdown_runtime, \
                patch.object(main, "CliInterface") as cli_interface_class:
            cli_interface_class.return_value.run.return_value = None
            main.main()

        startup_runtime.assert_called_once_with(context)
        shutdown_runtime.assert_called_once_with(context)
        cli_interface_class.assert_called_once_with(context)
        cli_interface_class.return_value.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
