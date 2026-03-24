"""Tests for reminder storage and notification handoff behavior."""

import unittest
from types import SimpleNamespace

from modules.reminders.reminders import Reminders
from tests.support.fakes import make_context


class _ReminderDatabase:
    """In-memory reminder database stub for backend tests."""

    def __init__(self):
        """Initialize row storage and query tracking."""

        self.executed = []
        self.rows = []
        self.next_id = 1

    def execute(self, query, params=()):
        """Record writes and mutate reminder rows for supported statements."""

        self.executed.append((query, params))
        normalized = " ".join(query.lower().split())

        if "insert into reminders" in normalized:
            reminder_id = self.next_id
            self.rows.append(
                {
                    "id": reminder_id,
                    "title": params[0],
                    "content": params[1],
                    "reminder_at": params[2],
                    "module_of_origin": params[3],
                    "notification_id": None,
                    "sent_at": None,
                    "created_at": "2026-03-24 00:00:00",
                }
            )
            self.next_id += 1
            return type("Cursor", (), {"lastrowid": reminder_id})()

        if normalized.startswith("delete from reminders where id ="):
            reminder_id = params[0]
            self.rows = [row for row in self.rows if row["id"] != reminder_id]
            return None

        if normalized.startswith("update reminders set notification_id = ?, sent_at = now() where id ="):
            notification_id, reminder_id = params
            for row in self.rows:
                if row["id"] == reminder_id:
                    row["notification_id"] = notification_id
                    row["sent_at"] = "now"
            return None

        return None

    def fetchOne(self, query, params=()):
        """Return one reminder row for supported lookup queries."""

        normalized = " ".join(query.lower().split())

        if "from reminders" not in normalized:
            return None

        if "order by id desc" in normalized:
            if not self.rows:
                return None
            return {"id": self.rows[-1]["id"]}

        reminder_id = params[0]
        for row in self.rows:
            if row["id"] == reminder_id:
                return dict(row)
        return None

    def fetchAll(self, query, params=()):
        """Return reminder rows for list and due-reminder queries."""

        normalized = " ".join(query.lower().split())

        if "from reminders" not in normalized:
            return []

        if "where reminder_at is not null" in normalized:
            return [dict(row) for row in self.rows if row["reminder_at"] is not None and row["sent_at"] is None]

        return [dict(row) for row in self.rows]


class _RecordingNotifications:
    """Notification service stub that records reminder handoff calls."""

    def __init__(self):
        """Initialize captured calls and deterministic IDs."""

        self.created = []
        self.sent = []
        self.next_id = 100

    def createNotification(self, source_module, title, content, timestamp):
        """Record notification creation and return a deterministic ID."""

        self.created.append((source_module, title, content, timestamp))
        value = self.next_id
        self.next_id += 1
        return value

    def sendNotification(self, notification_id):
        """Record notification sending."""

        self.sent.append(notification_id)


class RemindersTests(unittest.TestCase):
    """Validate reminder CRUD and notification delivery behavior."""

    def _create_reminders(self):
        """Build a reminder service with lightweight runtime doubles."""

        database = _ReminderDatabase()
        notifications = _RecordingNotifications()
        scheduler = SimpleNamespace(
            schedules={},
            getSchedule=lambda name: scheduler.schedules.get(name),
            addSchedule=lambda schedule: scheduler.schedules.setdefault(schedule.name, schedule),
        )
        context = make_context(
            database=database,
            extra={
                "notifications": notifications,
                "scheduler": scheduler,
            },
        )
        reminders = Reminders(context)
        return reminders, database, notifications, scheduler

    def test_create_reminder_persists_requested_fields_and_returns_id(self):
        """Reminder creation should store title, content, origin, datetime, and return the new ID."""

        reminders, database, _notifications, _scheduler = self._create_reminders()

        reminder_id = reminders.createReminder(
            title="Doctor appointment",
            content="Bring paperwork.",
            module_of_origin="calendar",
            reminder_at="17:00 24/03/2026",
        )

        self.assertEqual(reminder_id, 1)
        row = database.rows[0]
        self.assertEqual(row["title"], "Doctor appointment")
        self.assertEqual(row["content"], "Bring paperwork.")
        self.assertEqual(row["module_of_origin"], "calendar")
        self.assertEqual(row["reminder_at"], "2026-03-24 17:00:00")

    def test_get_and_delete_reminder_work_by_id(self):
        """Reminder retrieval and deletion should operate on the stored unique ID."""

        reminders, database, _notifications, _scheduler = self._create_reminders()
        reminders.createReminder("Stretch", "Stand up.", "system", "12:00 24/03/2026")

        row = reminders.getReminder(1)
        self.assertEqual(row["title"], "Stretch")

        reminders.deleteReminder(1)
        self.assertEqual(database.rows, [])

    def test_list_reminders_returns_all_rows(self):
        """Listing reminders should return the stored reminder collection."""

        reminders, _database, _notifications, _scheduler = self._create_reminders()
        reminders.createReminder("A", "First", "system", "08:00 24/03/2026")
        reminders.createReminder("B", "Second", "calendar", "09:00 24/03/2026")

        rows = reminders.listReminders()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "A")
        self.assertEqual(rows[1]["title"], "B")

    def test_send_reminder_creates_and_sends_notification(self):
        """Sending a reminder should create a notification and mark the reminder as sent."""

        reminders, database, notifications, _scheduler = self._create_reminders()
        reminders.createReminder("Stretch", "Stand up.", "system", "12:00 24/03/2026")

        notification_id = reminders.sendReminder(1)

        self.assertEqual(notification_id, 100)
        self.assertEqual(
            notifications.created,
            [("system", "Stretch", "Stand up.", "12:00 24/03/2026")],
        )
        self.assertEqual(notifications.sent, [100])
        self.assertEqual(database.rows[0]["notification_id"], 100)
        self.assertEqual(database.rows[0]["sent_at"], "now")

    def test_process_due_reminders_sends_each_pending_due_reminder(self):
        """The scheduler poller should send due reminders through notifications."""

        reminders, database, notifications, _scheduler = self._create_reminders()
        reminders.createReminder("A", "First", "system", "08:00 24/03/2026")
        reminders.createReminder("B", "Second", "calendar", "09:00 24/03/2026")

        rows = reminders.processDueReminders()

        self.assertEqual(len(rows), 2)
        self.assertEqual(len(notifications.created), 2)
        self.assertEqual(notifications.sent, [100, 101])
        self.assertEqual(database.rows[0]["sent_at"], "now")
        self.assertEqual(database.rows[1]["sent_at"], "now")


if __name__ == "__main__":
    unittest.main()
