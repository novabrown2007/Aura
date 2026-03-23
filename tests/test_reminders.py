"""Tests for reminder normalization and persistence behavior."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from modules.reminders.reminders import Reminders
from tests.support.fakes import make_context


class _RecordingDatabase:
    """Database stub that records reminder inserts for assertions."""

    def __init__(self):
        """Initialize captured query state for reminder tests."""

        self.executed = []

    def execute(self, query, params=()):
        """Record write queries and params without touching a real database."""

        self.executed.append((query, params))

    def fetchAll(self, _query, _params=()):
        """Return no reminder rows for list operations in unit tests."""

        return []


class _DueReminderDatabase:
    """Database stub that returns one due reminder and records delivery updates."""

    def __init__(self):
        """Initialize due reminder rows and executed query tracking."""

        self.executed = []
        self.rows = [
            {
                "id": 7,
                "title": "Stretch",
                "remind_at": "2026-03-23 17:28:00",
                "delivered_at": None,
                "created_at": "2026-03-23 12:00:00",
            }
        ]

    def execute(self, query, params=()):
        """Record updates and mark reminders delivered when requested."""

        self.executed.append((query, params))
        normalized = " ".join(query.lower().split())
        if normalized.startswith("update reminders set delivered_at = now()"):
            reminder_id = params[0]
            for row in self.rows:
                if row["id"] == reminder_id:
                    row["delivered_at"] = "now"

    def fetchAll(self, query, _params=()):
        """Return due reminders only until they are marked delivered."""

        normalized = " ".join(query.lower().split())
        if "where remind_at is not null" in normalized:
            return [row for row in self.rows if row["delivered_at"] is None]
        return list(self.rows)


class _RecordingEventManager:
    """Event manager stub that records emitted reminder events."""

    def __init__(self):
        """Initialize stored emitted events."""

        self.emitted = []

    def emit(self, event):
        """Record emitted events for assertions."""

        self.emitted.append(event)


class RemindersTests(unittest.TestCase):
    """Validate reminder datetime normalization before database writes."""

    def test_create_reminder_normalizes_labeled_datetime_input(self):
        """Ensure `HH:MM DD/MM/YYYY` inputs are normalized for MySQL DATETIME."""

        database = _RecordingDatabase()
        context = make_context(database=database)
        reminders = Reminders(context)

        reminders.createReminder("Doctor appointment", "17:00 24/03/2026")

        _query, params = database.executed[-1]
        self.assertEqual(params, ("Doctor appointment", "2026-03-24 17:00:00"))

    @patch("modules.reminders.reminders.datetime")
    def test_create_reminder_defaults_missing_date_to_today(self, mock_datetime):
        """Ensure time-only inputs default to the current local date."""

        database = _RecordingDatabase()
        context = make_context(database=database)
        reminders = Reminders(context)
        mock_datetime.now.return_value = datetime(2026, 3, 23, 8, 15, 0)
        mock_datetime.strptime = datetime.strptime

        reminders.createReminder("Pay bill", "17:28")

        _query, params = database.executed[-1]
        self.assertEqual(params, ("Pay bill", "2026-03-23 17:28:00"))

    def test_create_reminder_rejects_invalid_datetime_input(self):
        """Ensure invalid reminder times raise a clear validation error."""

        database = _RecordingDatabase()
        context = make_context(database=database)
        reminders = Reminders(context)

        with self.assertRaises(ValueError) as error:
            reminders.createReminder("Broken", "tomorrow sometime")

        self.assertIn("Invalid reminder", str(error.exception))

    def test_process_due_reminders_marks_delivery_and_emits_event(self):
        """Ensure due reminders trigger events and are marked delivered once."""

        database = _DueReminderDatabase()
        event_manager = _RecordingEventManager()
        context = make_context(
            database=database,
            extra={
                "eventManager": event_manager,
                "scheduler": SimpleNamespace(getSchedule=lambda _name: None, addSchedule=lambda _schedule: None),
            },
        )
        reminders = Reminders(context)

        rows = reminders.processDueReminders()

        self.assertEqual(len(rows), 1)
        self.assertEqual(database.rows[0]["delivered_at"], "now")
        self.assertEqual(len(event_manager.emitted), 1)
        self.assertEqual(event_manager.emitted[0].name, "reminder_triggered")
        self.assertEqual(event_manager.emitted[0].data["title"], "Stretch")


if __name__ == "__main__":
    unittest.main()
