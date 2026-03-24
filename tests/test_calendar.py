"""Tests for Aura's calendar backend module."""

import unittest

from modules.calendar.calendar import Calendar
from tests.support.fakes import make_context


class _CalendarDatabase:
    """In-memory stub covering the calendar SQL patterns used by tests."""

    def __init__(self):
        """Initialize in-memory calendar rows and query history."""

        self.executed = []
        self.next_calendar_id = 2
        self.next_event_id = 1
        self.next_task_id = 1
        self.next_reminder_id = 1
        self.next_exception_id = 1
        self.next_task_exception_id = 1
        self.next_reminder_exception_id = 1
        self.calendars = [
            {
                "id": 1,
                "name": "Aura",
                "description": "Default Aura calendar.",
                "color": "#3ea6ff",
                "timezone": "UTC",
                "visibility": "private",
                "is_default": True,
                "created_at": "2026-03-23 00:00:00",
            }
        ]
        self.events = []
        self.tasks = []
        self.reminders = []
        self.exceptions = []
        self.task_exceptions = []
        self.reminder_exceptions = []

    def execute(self, query, params=()):
        """Record writes and mutate in-memory rows for supported statements."""

        self.executed.append((query, params))
        normalized = " ".join(query.lower().split())

        if normalized.startswith("update calendar_calendars set is_default = 0"):
            for row in self.calendars:
                row["is_default"] = False
            return

        if "insert into calendar_calendars" in normalized:
            self.calendars.append(
                {
                    "id": self.next_calendar_id,
                    "name": params[0],
                    "description": params[1],
                    "color": params[2],
                    "timezone": params[3],
                    "visibility": params[4],
                    "is_default": bool(params[5]),
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_calendar_id += 1
            return

        if "insert into calendar_events" in normalized:
            self.events.append(
                {
                    "id": self.next_event_id,
                    "calendar_id": params[0],
                    "title": params[1],
                    "description": params[2],
                    "location": params[3],
                    "attendees": params[4],
                    "start_at": params[5],
                    "end_at": params[6],
                    "all_day": bool(params[7]),
                    "status": params[8],
                    "organizer": params[9],
                    "timezone": params[10],
                    "visibility": params[11],
                    "categories": params[12],
                    "notification_preferences": params[13],
                    "linked_task_id": params[14],
                    "recurrence_type": params[15],
                    "recurrence_interval": params[16],
                    "recurrence_until": params[17],
                    "recurrence_count": params[18],
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_event_id += 1
            return

        if "insert into calendar_tasks" in normalized:
            self.tasks.append(
                {
                    "id": self.next_task_id,
                    "calendar_id": params[0],
                    "linked_event_id": params[1],
                    "title": params[2],
                    "description": params[3],
                    "timezone": params[4],
                    "categories": params[5],
                    "notification_preferences": params[6],
                    "due_at": params[7],
                    "priority": params[8],
                    "status": params[9],
                    "recurrence_type": params[10],
                    "recurrence_interval": params[11],
                    "recurrence_until": params[12],
                    "recurrence_count": params[13],
                    "completed_at": None,
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_task_id += 1
            return

        if "insert into calendar_reminders" in normalized:
            self.reminders.append(
                {
                    "id": self.next_reminder_id,
                    "calendar_id": params[0],
                    "event_id": params[1],
                    "task_id": params[2],
                    "title": params[3],
                    "notes": params[4],
                    "timezone": params[5],
                    "notification_preferences": params[6],
                    "remind_at": params[7],
                    "recurrence_type": params[8],
                    "recurrence_interval": params[9],
                    "recurrence_until": params[10],
                    "recurrence_count": params[11],
                    "delivered_at": None,
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_reminder_id += 1
            return

        if "insert into calendar_event_exceptions" in normalized:
            self.exceptions.append(
                {
                    "id": self.next_exception_id,
                    "event_id": params[0],
                    "occurrence_start": params[1],
                    "exception_type": params[2],
                    "override_title": params[3],
                    "override_description": params[4],
                    "override_location": params[5],
                    "override_attendees": params[6],
                    "override_start_at": params[7],
                    "override_end_at": params[8],
                    "override_all_day": params[9],
                    "override_status": params[10],
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_exception_id += 1
            return

        if "insert into calendar_task_exceptions" in normalized:
            self.task_exceptions.append(
                {
                    "id": self.next_task_exception_id,
                    "task_id": params[0],
                    "occurrence_due_at": params[1],
                    "exception_type": params[2],
                    "override_title": params[3],
                    "override_description": params[4],
                    "override_due_at": params[5],
                    "override_priority": params[6],
                    "override_status": params[7],
                    "override_categories": params[8],
                    "override_notification_preferences": params[9],
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_task_exception_id += 1
            return

        if "insert into calendar_reminder_exceptions" in normalized:
            self.reminder_exceptions.append(
                {
                    "id": self.next_reminder_exception_id,
                    "reminder_id": params[0],
                    "occurrence_remind_at": params[1],
                    "exception_type": params[2],
                    "override_title": params[3],
                    "override_notes": params[4],
                    "override_remind_at": params[5],
                    "override_notification_preferences": params[6],
                    "created_at": "2026-03-23 00:00:00",
                }
            )
            self.next_reminder_exception_id += 1
            return

        if normalized.startswith("update calendar_reminders set delivered_at = now()"):
            reminder_id = params[0]
            for row in self.reminders:
                if row["id"] == reminder_id:
                    row["delivered_at"] = "now"
            return

        if normalized.startswith("delete from calendar_reminders where event_id ="):
            event_id = params[0]
            self.reminders = [row for row in self.reminders if row["event_id"] != event_id]
            return

        if normalized.startswith("delete from calendar_event_exceptions where event_id ="):
            event_id = params[0]
            self.exceptions = [row for row in self.exceptions if row["event_id"] != event_id]
            return

        if normalized.startswith("delete from calendar_task_exceptions where task_id ="):
            task_id = params[0]
            self.task_exceptions = [row for row in self.task_exceptions if row["task_id"] != task_id]
            return

        if normalized.startswith("delete from calendar_reminder_exceptions where reminder_id ="):
            reminder_id = params[0]
            self.reminder_exceptions = [
                row for row in self.reminder_exceptions if row["reminder_id"] != reminder_id
            ]
            return

        if normalized.startswith("delete from calendar_events where id ="):
            event_id = params[0]
            self.events = [row for row in self.events if row["id"] != event_id]
            return

        if normalized.startswith("delete from calendar_reminders where task_id ="):
            task_id = params[0]
            self.reminders = [row for row in self.reminders if row["task_id"] != task_id]
            return

        if normalized.startswith("delete from calendar_tasks where id ="):
            task_id = params[0]
            self.tasks = [row for row in self.tasks if row["id"] != task_id]
            return

        if normalized.startswith("delete from calendar_reminders where id ="):
            reminder_id = params[0]
            self.reminders = [row for row in self.reminders if row["id"] != reminder_id]
            return

        if normalized.startswith("update calendar_events set "):
            self._update_row(self.events, params, normalized)
            return

        if normalized.startswith("update calendar_tasks set "):
            self._update_row(self.tasks, params, normalized)
            return

        if normalized.startswith("update calendar_reminders set "):
            self._update_row(self.reminders, params, normalized)

    def fetchOne(self, query, params=()):
        """Return one row for supported single-row calendar lookups."""

        normalized = " ".join(query.lower().split())

        if "from calendar_calendars" in normalized and "where is_default = 1" in normalized:
            for row in self.calendars:
                if row["is_default"]:
                    return {"id": row["id"], "name": row["name"]}
            return None

        if "from calendar_calendars" in normalized and "where id = ?" in normalized:
            row_id = params[0]
            return self._find_by_id(self.calendars, row_id)

        if "from calendar_events" in normalized and "where id = ?" in normalized:
            row_id = params[0]
            return self._find_by_id(self.events, row_id)

        if "from calendar_tasks" in normalized and "where id = ?" in normalized:
            row_id = params[0]
            return self._find_by_id(self.tasks, row_id)

        if "from calendar_reminders" in normalized and "where id = ?" in normalized:
            row_id = params[0]
            return self._find_by_id(self.reminders, row_id)

        return None

    def fetchAll(self, query, params=()):
        """Return rows for supported list/search calendar queries."""

        normalized = " ".join(query.lower().split())

        if "from calendar_calendars" in normalized:
            rows = list(self.calendars)
            rows.sort(key=lambda row: (not row["is_default"], row["name"]))
            return [dict(row) for row in rows]

        if "from calendar_events" in normalized:
            rows = list(self.events)
            if "where calendar_id = ?" in normalized:
                calendar_id = params[0]
                rows = [row for row in rows if row["calendar_id"] == calendar_id]
            rows.sort(key=lambda row: (row["start_at"], row["id"]))
            return [dict(row) for row in rows]

        if "from calendar_tasks" in normalized:
            rows = list(self.tasks)
            rows.sort(key=lambda row: (row["due_at"] or "", row["id"]))
            return [dict(row) for row in rows]

        if "from calendar_event_exceptions" in normalized:
            event_id = params[0]
            rows = [row for row in self.exceptions if row["event_id"] == event_id]
            rows.sort(key=lambda row: (row["occurrence_start"], row["id"]))
            return [dict(row) for row in rows]

        if "from calendar_task_exceptions" in normalized:
            task_id = params[0]
            rows = [row for row in self.task_exceptions if row["task_id"] == task_id]
            rows.sort(key=lambda row: (row["occurrence_due_at"], row["id"]))
            return [dict(row) for row in rows]

        if "from calendar_reminder_exceptions" in normalized:
            reminder_id = params[0]
            rows = [row for row in self.reminder_exceptions if row["reminder_id"] == reminder_id]
            rows.sort(key=lambda row: (row["occurrence_remind_at"], row["id"]))
            return [dict(row) for row in rows]

        if "from calendar_reminders" in normalized and "where delivered_at is null and remind_at <= now()" in normalized:
            rows = [row for row in self.reminders if row["delivered_at"] is None]
            rows.sort(key=lambda row: (row["remind_at"], row["id"]))
            return [dict(row) for row in rows]

        if "from calendar_reminders" in normalized:
            rows = list(self.reminders)
            rows.sort(key=lambda row: (row["remind_at"], row["id"]))
            return [dict(row) for row in rows]

        return []

    @staticmethod
    def _find_by_id(rows, row_id):
        """Return a copied row by ID when it exists."""

        for row in rows:
            if row["id"] == row_id:
                return dict(row)
        return None

    @staticmethod
    def _update_row(rows, params, normalized_query):
        """Apply a generic update statement to an in-memory row list."""

        row_id = params[-1]
        row = None
        for candidate in rows:
            if candidate["id"] == row_id:
                row = candidate
                break

        assignments = normalized_query.split(" set ", 1)[1].split(" where ", 1)[0].split(",")
        for assignment, value in zip(assignments, params[:-1]):
            key = assignment.split("=", 1)[0].strip()
            row[key] = value


class _RecordingEventManager:
    """Event manager stub that records emitted calendar reminder events."""

    def __init__(self):
        """Initialize emitted-event storage."""

        self.emitted = []

    def emit(self, event):
        """Record one emitted event."""

        self.emitted.append(event)


class _RecordingScheduler:
    """Scheduler stub that stores registered schedules by name."""

    def __init__(self):
        """Initialize in-memory schedule storage."""

        self.schedules = {}

    def getSchedule(self, name):
        """Return one schedule by name when it exists."""

        return self.schedules.get(name)

    def addSchedule(self, schedule):
        """Store a schedule registration."""

        self.schedules[schedule.name] = schedule


class CalendarTests(unittest.TestCase):
    """Validate the core calendar backend without any interface layer."""

    def _build_calendar(self):
        """Create a calendar backend with in-memory persistence stubs."""

        database = _CalendarDatabase()
        scheduler = _RecordingScheduler()
        event_manager = _RecordingEventManager()
        context = make_context(
            database=database,
            extra={"scheduler": scheduler, "eventManager": event_manager},
        )
        return Calendar(context), database, scheduler, event_manager

    def test_initialization_ensures_default_calendar_and_schedule(self):
        """Ensure the calendar module registers its reminder polling schedule."""

        calendar, _database, scheduler, _event_manager = self._build_calendar()

        self.assertEqual(calendar.getDefaultCalendarId(), 1)
        self.assertIn("calendar_poll_due_reminders", scheduler.schedules)

    def test_create_event_persists_utc_storage_and_localized_reads(self):
        """Ensure events store UTC timestamps while reads stay in the event timezone."""

        calendar, database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(
            title="Team sync",
            start_at="24/03/2026 09:00",
            end_at="24/03/2026 10:00",
            attendees=["alice@example.com", "bob@example.com"],
            organizer="nova@example.com",
            timezone="America/Toronto",
            categories=["work", "meetings"],
            recurrence_type="weekly",
            recurrence_interval=1,
            recurrence_count=3,
        )

        event = calendar.getEvent(1)
        self.assertEqual(event["attendees"], ["alice@example.com", "bob@example.com"])
        self.assertEqual(event["organizer"], "nova@example.com")
        self.assertEqual(event["timezone"], "America/Toronto")
        self.assertEqual(event["categories"], ["work", "meetings"])
        self.assertEqual(event["recurrence_type"], "weekly")
        self.assertEqual(database.events[0]["start_at"], "2026-03-24 13:00:00")
        self.assertEqual(event["start_at"], "2026-03-24 09:00:00")

    def test_list_events_for_range_expands_recurring_series(self):
        """Ensure recurring events expand into concrete instances for range views."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(
            title="Standup",
            start_at="2026-03-24 09:00",
            end_at="2026-03-24 09:30",
            recurrence_type="weekly",
            recurrence_count=3,
        )

        rows = calendar.listEventsForRange("2026-03-24 00:00", "2026-04-07 23:59")

        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["is_recurring_instance"] for row in rows))
        self.assertEqual(rows[0]["series_id"], 1)

    def test_search_events_filters_by_attendee_and_text(self):
        """Ensure event search supports attendee and text matching."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(
            title="Planning meeting",
            start_at="2026-03-24 11:00",
            attendees=["alice@example.com", "bob@example.com"],
            description="Roadmap review",
        )
        calendar.createEvent(
            title="Personal errand",
            start_at="2026-03-24 15:00",
            attendees=["nova@example.com"],
        )

        rows = calendar.searchEvents(query="planning", attendee="alice@example.com")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Planning meeting")

    def test_cancel_occurrence_skips_one_generated_recurring_instance(self):
        """Ensure recurrence cancellation exceptions suppress one occurrence."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(
            title="Standup",
            start_at="2026-03-24 09:00",
            end_at="2026-03-24 09:30",
            recurrence_type="weekly",
            recurrence_count=3,
        )
        calendar.cancelOccurrence(1, "2026-03-31 09:00")

        rows = calendar.listEventsForRange("2026-03-24 00:00", "2026-04-07 23:59")

        self.assertEqual(len(rows), 2)
        self.assertEqual(
            [row["start_at"] for row in rows],
            ["2026-03-24 09:00:00", "2026-04-07 09:00:00"],
        )

    def test_update_occurrence_overrides_one_generated_instance(self):
        """Ensure recurrence override exceptions change one generated occurrence only."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(
            title="Standup",
            start_at="2026-03-24 09:00",
            end_at="2026-03-24 09:30",
            attendees=["alice@example.com"],
            recurrence_type="weekly",
            recurrence_count=3,
        )
        calendar.updateOccurrence(
            1,
            "2026-03-31 09:00",
            title="Standup moved",
            start_at="2026-03-31 10:00",
            end_at="2026-03-31 10:45",
            attendees=["alice@example.com", "bob@example.com"],
        )

        rows = calendar.listEventsForRange("2026-03-24 00:00", "2026-04-07 23:59")

        self.assertEqual(len(rows), 3)
        overridden = rows[1]
        self.assertEqual(overridden["title"], "Standup moved")
        self.assertEqual(overridden["start_at"], "2026-03-31 10:00:00")
        self.assertEqual(overridden["end_at"], "2026-03-31 10:45:00")
        self.assertEqual(overridden["attendees"], ["alice@example.com", "bob@example.com"])
        self.assertTrue(overridden["has_exception"])

    def test_task_occurrence_exception_overrides_one_generated_instance(self):
        """Ensure recurring tasks support one-instance override exceptions."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createTask(
            title="Daily writeup",
            due_at="24/03/2026 09:00",
            timezone="America/Toronto",
            recurrence_type="daily",
            recurrence_count=3,
        )
        calendar.updateTaskOccurrence(
            1,
            "25/03/2026 09:00",
            title="Daily writeup delayed",
            due_at="25/03/2026 10:30",
            priority="high",
        )

        rows = calendar.searchTasks(due_after="24/03/2026 00:00", due_before="26/03/2026 23:59")

        self.assertEqual(len(rows), 3)
        overridden = rows[1]
        self.assertEqual(overridden["title"], "Daily writeup delayed")
        self.assertEqual(overridden["due_at"], "2026-03-25 10:30:00")
        self.assertEqual(overridden["priority"], "high")
        self.assertTrue(overridden["has_exception"])

    def test_reminder_occurrence_exception_can_cancel_one_instance(self):
        """Ensure recurring reminders support one-instance cancellation exceptions."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createReminder(
            title="Drink water",
            remind_at="24/03/2026 09:00",
            timezone="America/Toronto",
            recurrence_type="daily",
            recurrence_count=3,
        )
        calendar.cancelReminderOccurrence(1, "25/03/2026 09:00")

        rows = calendar.searchReminders(
            remind_after="24/03/2026 00:00",
            remind_before="26/03/2026 23:59",
        )

        self.assertEqual([row["remind_at"] for row in rows], ["2026-03-24 09:00:00", "2026-03-26 09:00:00"])

    def test_update_event_series_following_splits_series(self):
        """Ensure following-scope updates stop the old series and create a new one."""

        calendar, database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(
            title="Standup",
            start_at="2026-03-24 09:00",
            end_at="2026-03-24 09:30",
            recurrence_type="weekly",
            recurrence_count=4,
        )

        calendar.updateEventSeries(
            1,
            scope="following",
            occurrence_start="2026-04-07 09:00",
            title="Standup phase 2",
        )

        self.assertEqual(len(database.events), 2)
        self.assertEqual(database.events[0]["recurrence_until"], "2026-03-31 09:00:00")

    def test_update_task_series_following_splits_series(self):
        """Ensure following-scope task updates stop the old series and create a new one."""

        calendar, database, _scheduler, _event_manager = self._build_calendar()

        calendar.createTask(
            title="Daily writeup",
            due_at="2026-03-24 09:00",
            recurrence_type="daily",
            recurrence_count=4,
        )

        calendar.updateTaskSeries(
            1,
            scope="following",
            occurrence_due_at="2026-03-26 09:00",
            title="Daily writeup phase 2",
        )

        self.assertEqual(len(database.tasks), 2)
        self.assertEqual(database.tasks[0]["recurrence_until"], "2026-03-25 09:00:00")
        self.assertEqual(database.tasks[1]["title"], "Daily writeup phase 2")

    def test_update_reminder_series_following_splits_series(self):
        """Ensure following-scope reminder updates stop the old series and create a new one."""

        calendar, database, _scheduler, _event_manager = self._build_calendar()

        calendar.createReminder(
            title="Hydrate",
            remind_at="2026-03-24 09:00",
            recurrence_type="daily",
            recurrence_count=4,
        )

        calendar.updateReminderSeries(
            1,
            scope="following",
            occurrence_remind_at="2026-03-26 09:00",
            title="Hydrate phase 2",
        )

        self.assertEqual(len(database.reminders), 2)
        self.assertEqual(database.reminders[0]["recurrence_until"], "2026-03-25 09:00:00")
        self.assertEqual(database.reminders[1]["title"], "Hydrate phase 2")

    def test_timezone_conversion_handles_dst_spring_forward(self):
        """Ensure timezone conversion respects DST transitions using real timezone data."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        converted = calendar.convertDateTimeBetweenTimezones(
            "2026-03-08 01:30",
            "America/Toronto",
            "UTC",
        )

        self.assertEqual(converted, "2026-03-08 06:30:00")

    def test_timezone_conversion_handles_dst_fall_back(self):
        """Ensure timezone conversion respects late-year DST offsets."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        converted = calendar.convertDateTimeBetweenTimezones(
            "2026-11-02 09:00",
            "America/Toronto",
            "UTC",
        )

        self.assertEqual(converted, "2026-11-02 14:00:00")

    def test_search_tasks_filters_by_status_and_priority(self):
        """Ensure task search supports status and priority filters."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createTask(title="Pay rent", due_at="2026-03-25 12:00", priority="high")
        calendar.createTask(title="Water plants", due_at="2026-03-25 18:00", priority="low")
        calendar.updateTask(1, status="completed", completed_at="2026-03-25 11:00")

        rows = calendar.searchTasks(status="completed", priority="high")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Pay rent")

    def test_create_and_process_calendar_reminder(self):
        """Ensure calendar reminders emit events and mark delivery state."""

        calendar, database, _scheduler, event_manager = self._build_calendar()

        calendar.createReminder(title="Leave now", remind_at="2026-03-23 17:28")
        rows = calendar.processDueReminders()

        self.assertEqual(len(rows), 1)
        self.assertEqual(database.reminders[0]["delivered_at"], "now")
        self.assertEqual(len(event_manager.emitted), 1)
        self.assertEqual(event_manager.emitted[0].name, "calendar_reminder_triggered")

    def test_build_day_view_groups_events_tasks_and_reminders(self):
        """Ensure day view returns events, tasks, and reminders together."""

        calendar, _database, _scheduler, _event_manager = self._build_calendar()

        calendar.createEvent(title="Meeting", start_at="2026-03-24 09:00", end_at="2026-03-24 10:00")
        calendar.createTask(title="Call bank", due_at="2026-03-24 15:00")
        calendar.createReminder(title="Prep notes", remind_at="2026-03-24 08:30")

        day_view = calendar.buildDayView("2026-03-24")

        self.assertEqual(day_view["day"], "2026-03-24")
        self.assertEqual(len(day_view["events"]), 1)
        self.assertEqual(len(day_view["tasks"]), 1)
        self.assertEqual(len(day_view["reminders"]), 1)


if __name__ == "__main__":
    unittest.main()
