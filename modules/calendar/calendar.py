"""Calendar data layer for Aura's private scheduling system."""

from __future__ import annotations

import calendar as month_calendar
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional
from zoneinfo import ZoneInfo

from core.threading.events.events import Event
from core.threading.scheduler.schedule import Schedule

RECURRENCE_TYPES = {"daily", "weekly", "monthly", "yearly"}


class Calendar:
    """
    Calendar backend for calendars, events, tasks, and reminders.

    This module is the storage and query foundation for Aura's private
    calendar system. It handles recurring events, reminder delivery,
    attendees, and search/filter queries so future command and interface
    layers can stay thin.
    """

    def __init__(self, context):
        """
        Initialize the calendar module and register reminder polling.

        Args:
            context:
                Runtime context containing the database, scheduler, and event
                manager used by the rest of Aura.
        """

        self.context = context
        self.database = context.database
        self.logger = context.logger.getChild("Calendar") if context.logger else None

        self._registerReminderPollingSchedule()
        self.ensureDefaultCalendar()

        if self.logger:
            self.logger.info("Initialized.")

    def _registerReminderPollingSchedule(self):
        """
        Register a repeating scheduler job that checks calendar reminders.
        """

        scheduler = getattr(self.context, "scheduler", None)
        if scheduler is None:
            return

        schedule_name = "calendar_poll_due_reminders"
        if scheduler.getSchedule(schedule_name) is not None:
            return

        scheduler.addSchedule(
            Schedule(
                name=schedule_name,
                target=self.processDueReminders,
                interval=15.0,
            )
        )

    def ensureDefaultCalendar(self):
        """
        Ensure Aura always has one default calendar available.
        """

        if not self.database:
            return

        existing = self.database.fetchOne(
            """
            SELECT id, name
            FROM calendar_calendars
            WHERE is_default = 1
            LIMIT 1
            """
        )

        if existing:
            return

        self.database.execute(
            """
            INSERT INTO calendar_calendars (name, description, color, is_default)
            VALUES (?, ?, ?, ?)
            """,
            ("Aura", "Default Aura calendar.", "#3ea6ff", True),
        )

    def createCalendar(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        timezone: str = "UTC",
        visibility: str = "private",
        is_default: bool = False,
    ):
        """
        Create a calendar container.
        """

        if not self.database:
            return

        if is_default:
            self.database.execute(
                "UPDATE calendar_calendars SET is_default = 0 WHERE is_default = 1"
            )

        self.database.execute(
            """
            INSERT INTO calendar_calendars (name, description, color, timezone, visibility, is_default)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, description, color, timezone, visibility, is_default),
        )

    def listCalendars(self):
        """
        Return all calendar containers ordered by default status and name.
        """

        if not self.database:
            return []

        return self.database.fetchAll(
            """
            SELECT id, name, description, color, timezone, visibility, is_default, created_at
            FROM calendar_calendars
            ORDER BY is_default DESC, name ASC
            """
        )

    def getDefaultCalendarId(self) -> Optional[int]:
        """
        Return the default calendar ID when one exists.
        """

        if not self.database:
            return None

        row = self.database.fetchOne(
            """
            SELECT id
            FROM calendar_calendars
            WHERE is_default = 1
            LIMIT 1
            """
        )
        if row:
            return int(row["id"])
        return None

    def createEvent(
        self,
        title: str,
        start_at: str,
        end_at: Optional[str] = None,
        calendar_id: Optional[int] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[Iterable[str] | str] = None,
        organizer: Optional[str] = None,
        timezone: Optional[str] = None,
        visibility: str = "private",
        categories: Optional[Iterable[str] | str] = None,
        notification_preferences: Optional[dict] = None,
        linked_task_id: Optional[int] = None,
        all_day: bool = False,
        status: str = "confirmed",
        recurrence_type: Optional[str] = None,
        recurrence_interval: int = 1,
        recurrence_until: Optional[str] = None,
        recurrence_count: Optional[int] = None,
    ):
        """
        Create a calendar event.
        """

        if not self.database:
            return

        resolved_calendar_id = self._resolveCalendarId(calendar_id)
        event_timezone = timezone or self.getCalendarTimezone(resolved_calendar_id)
        normalized_start_at = self._normalizeDateTimeValue(
            start_at,
            allow_date_only=all_day,
            source_timezone=event_timezone,
        )
        normalized_end_at = (
            self._normalizeDateTimeValue(
                end_at,
                allow_date_only=all_day,
                source_timezone=event_timezone,
            )
            if end_at is not None
            else None
        )
        normalized_recurrence = self._normalizeRecurrence(
            recurrence_type=recurrence_type,
            recurrence_interval=recurrence_interval,
            recurrence_until=recurrence_until,
            recurrence_count=recurrence_count,
            source_timezone=event_timezone,
            allow_date_only=all_day,
        )

        cursor = self.database.execute(
            """
            INSERT INTO calendar_events (
                calendar_id, title, description, location, attendees, start_at, end_at, all_day,
                status, organizer, timezone, visibility, categories, notification_preferences,
                linked_task_id, recurrence_type, recurrence_interval, recurrence_until, recurrence_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_calendar_id,
                title,
                description,
                location,
                self._serializeAttendees(attendees),
                normalized_start_at,
                normalized_end_at,
                all_day,
                status,
                organizer,
                event_timezone,
                visibility,
                self._serializeStringList(categories),
                self._serializeJsonValue(notification_preferences),
                linked_task_id,
                normalized_recurrence["recurrence_type"],
                normalized_recurrence["recurrence_interval"],
                normalized_recurrence["recurrence_until"],
                normalized_recurrence["recurrence_count"],
            ),
        )
        event_id = self._resolveInsertedRowId(cursor, "calendar_events")
        self._queueEventRemindersFromPreferences(
            event_id=event_id,
            title=title,
            description=description,
            start_at=normalized_start_at,
            timezone=event_timezone,
            notification_preferences=notification_preferences,
        )
        return event_id

    def listEventsForRange(self, start_at: str, end_at: str, calendar_id: Optional[int] = None):
        """
        Return events overlapping the provided time range.
        """

        if not self.database:
            return []

        query_timezone = self.getCalendarTimezone(calendar_id)
        range_start = self._parseDateTime(
            self._normalizeDateTimeValue(
                start_at,
                source_timezone=query_timezone,
                target_timezone=query_timezone,
            )
        )
        range_end = self._parseDateTime(
            self._normalizeDateTimeValue(
                end_at,
                source_timezone=query_timezone,
                target_timezone=query_timezone,
            )
        )

        events = []
        for row in self._fetchStoredEvents(calendar_id=calendar_id):
            if row.get("recurrence_type"):
                events.extend(self._expandRecurringEvent(row, range_start, range_end))
            elif self._eventOverlapsRange(row, range_start, range_end):
                events.append(row)

        events.sort(key=lambda row: (row.get("start_at") or "", row.get("id") or 0))
        return events

    def listEventsForDay(self, day: str, calendar_id: Optional[int] = None):
        """
        Return events that occur on a specific day.
        """

        normalized_day = self._normalizeDateValue(day)
        range_start = f"{normalized_day} 00:00:00"
        range_end = f"{normalized_day} 23:59:59"
        return self.listEventsForRange(range_start, range_end, calendar_id=calendar_id)

    def searchEvents(
        self,
        query: Optional[str] = None,
        calendar_id: Optional[int] = None,
        start_at: Optional[str] = None,
        end_at: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        attendee: Optional[str] = None,
        all_day: Optional[bool] = None,
    ):
        """
        Search and filter events using textual and structural criteria.
        """

        if start_at is not None and end_at is not None:
            rows = self.listEventsForRange(start_at, end_at, calendar_id=calendar_id)
        else:
            rows = self._fetchStoredEvents(calendar_id=calendar_id)

        query_value = (query or "").strip().lower()
        location_value = (location or "").strip().lower()
        attendee_value = (attendee or "").strip().lower()
        status_value = (status or "").strip().lower()

        filtered = []
        for row in rows:
            title_text = str(row.get("title") or "").lower()
            description_text = str(row.get("description") or "").lower()
            location_text = str(row.get("location") or "").lower()
            attendees = [str(value).lower() for value in row.get("attendees", [])]

            if query_value and query_value not in title_text and query_value not in description_text:
                continue
            if location_value and location_value not in location_text:
                continue
            if attendee_value and attendee_value not in attendees:
                continue
            if status_value and str(row.get("status") or "").lower() != status_value:
                continue
            if all_day is not None and bool(row.get("all_day")) != bool(all_day):
                continue
            filtered.append(row)

        return filtered

    def getEvent(self, event_id: int):
        """
        Return one stored event by ID.
        """

        if not self.database:
            return None

        row = self.database.fetchOne(
            """
            SELECT id, calendar_id, title, description, location, attendees, organizer, timezone,
                   visibility, categories, notification_preferences, linked_task_id, start_at, end_at,
                   all_day, status, recurrence_type, recurrence_interval, recurrence_until,
                   recurrence_count, created_at
            FROM calendar_events
            WHERE id = ?
            """,
            (event_id,),
        )
        return self._prepareEventRow(row)

    def updateEvent(self, event_id: int, **fields):
        """
        Update one event using a dynamic field map.
        """

        normalized_fields = dict(fields)
        current = self.getEvent(event_id) or {}
        event_timezone = normalized_fields.get("timezone", current.get("timezone", "UTC"))

        if "attendees" in normalized_fields:
            normalized_fields["attendees"] = self._serializeAttendees(normalized_fields["attendees"])
        if "categories" in normalized_fields:
            normalized_fields["categories"] = self._serializeStringList(normalized_fields["categories"])
        if "notification_preferences" in normalized_fields:
            normalized_fields["notification_preferences"] = self._serializeJsonValue(
                normalized_fields["notification_preferences"]
            )

        recurrence_keys = {
            "recurrence_type",
            "recurrence_interval",
            "recurrence_until",
            "recurrence_count",
        }
        if recurrence_keys.intersection(normalized_fields):
            normalized_recurrence = self._normalizeRecurrence(
                recurrence_type=normalized_fields.get("recurrence_type", current.get("recurrence_type")),
                recurrence_interval=normalized_fields.get(
                    "recurrence_interval",
                    current.get("recurrence_interval", 1),
                ),
                recurrence_until=normalized_fields.get(
                    "recurrence_until",
                    current.get("recurrence_until"),
                ),
                recurrence_count=normalized_fields.get(
                    "recurrence_count",
                    current.get("recurrence_count"),
                ),
                source_timezone=event_timezone,
                allow_date_only=bool(normalized_fields.get("all_day", current.get("all_day"))),
            )
            normalized_fields.update(normalized_recurrence)

        for field_name in ("start_at", "end_at"):
            if normalized_fields.get(field_name) is not None:
                normalized_fields[field_name] = self._normalizeDateTimeValue(
                    normalized_fields[field_name],
                    allow_date_only=bool(normalized_fields.get("all_day", current.get("all_day"))),
                    source_timezone=event_timezone,
                )

        self._updateRow(
            table_name="calendar_events",
            row_id=event_id,
            fields=normalized_fields,
            allowed_fields={
                "calendar_id",
                "title",
                "description",
                "location",
                "attendees",
                "organizer",
                "timezone",
                "visibility",
                "categories",
                "notification_preferences",
                "linked_task_id",
                "start_at",
                "end_at",
                "all_day",
                "status",
                "recurrence_type",
                "recurrence_interval",
                "recurrence_until",
                "recurrence_count",
            },
            datetime_fields=set(),
        )

    def deleteEvent(self, event_id: int):
        """
        Delete one calendar event and any attached calendar reminders.
        """

        if not self.database:
            return

        self.database.execute("DELETE FROM calendar_event_exceptions WHERE event_id = ?", (event_id,))
        self.database.execute("DELETE FROM calendar_reminders WHERE event_id = ?", (event_id,))
        self.database.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))

    def createRecurrenceException(
        self,
        event_id: int,
        occurrence_start: str,
        exception_type: str = "override",
        **overrides,
    ):
        """
        Create a recurrence exception for one event instance.

        Supported exception types:
        - `cancel`: suppress one generated occurrence
        - `override`: replace selected fields for one generated occurrence
        """

        if not self.database:
            return

        event = self.getEvent(event_id)
        if event is None:
            raise ValueError("Event does not exist.")

        event_timezone = str(event.get("timezone") or "UTC")
        normalized_occurrence_start = self._normalizeDateTimeValue(
            occurrence_start,
            allow_date_only=bool(event.get("all_day")),
            source_timezone=event_timezone,
        )
        normalized_type = str(exception_type).strip().lower()
        if normalized_type not in {"cancel", "override"}:
            raise ValueError("Invalid exception type. Use cancel or override.")

        self.database.execute(
            """
            INSERT INTO calendar_event_exceptions (
                event_id, occurrence_start, exception_type, override_title,
                override_description, override_location, override_attendees,
                override_start_at, override_end_at, override_all_day, override_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(event_id),
                normalized_occurrence_start,
                normalized_type,
                overrides.get("title"),
                overrides.get("description"),
                overrides.get("location"),
                self._serializeAttendees(overrides.get("attendees"))
                if "attendees" in overrides
                else None,
                self._normalizeDateTimeValue(
                    overrides["start_at"],
                    allow_date_only=bool(overrides.get("all_day", event.get("all_day"))),
                    source_timezone=event_timezone,
                )
                if overrides.get("start_at") is not None
                else None,
                self._normalizeDateTimeValue(
                    overrides["end_at"],
                    allow_date_only=bool(overrides.get("all_day", event.get("all_day"))),
                    source_timezone=event_timezone,
                )
                if overrides.get("end_at") is not None
                else None,
                overrides.get("all_day"),
                overrides.get("status"),
            ),
        )

    def cancelOccurrence(self, event_id: int, occurrence_start: str):
        """
        Create a cancellation exception for one recurring event instance.
        """

        self.createRecurrenceException(
            event_id=event_id,
            occurrence_start=occurrence_start,
            exception_type="cancel",
        )

    def updateOccurrence(self, event_id: int, occurrence_start: str, **overrides):
        """
        Create an override exception for one recurring event instance.
        """

        self.createRecurrenceException(
            event_id=event_id,
            occurrence_start=occurrence_start,
            exception_type="override",
            **overrides,
        )

    def createTask(
        self,
        title: str,
        due_at: Optional[str] = None,
        calendar_id: Optional[int] = None,
        linked_event_id: Optional[int] = None,
        description: Optional[str] = None,
        timezone: Optional[str] = None,
        categories: Optional[Iterable[str] | str] = None,
        notification_preferences: Optional[dict] = None,
        priority: str = "normal",
        status: str = "pending",
        recurrence_type: Optional[str] = None,
        recurrence_interval: int = 1,
        recurrence_until: Optional[str] = None,
        recurrence_count: Optional[int] = None,
    ):
        """
        Create a calendar task.
        """

        if not self.database:
            return

        resolved_calendar_id = self._resolveCalendarId(calendar_id)
        task_timezone = timezone or self.getCalendarTimezone(resolved_calendar_id)
        normalized_due_at = (
            self._normalizeDateTimeValue(due_at, source_timezone=task_timezone)
            if due_at is not None
            else None
        )
        normalized_recurrence = self._normalizeRecurrence(
            recurrence_type=recurrence_type,
            recurrence_interval=recurrence_interval,
            recurrence_until=recurrence_until,
            recurrence_count=recurrence_count,
            source_timezone=task_timezone,
        )

        self.database.execute(
            """
            INSERT INTO calendar_tasks (
                calendar_id, linked_event_id, title, description, timezone, categories,
                notification_preferences, due_at, priority, status, recurrence_type,
                recurrence_interval, recurrence_until, recurrence_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_calendar_id,
                linked_event_id,
                title,
                description,
                task_timezone,
                self._serializeStringList(categories),
                self._serializeJsonValue(notification_preferences),
                normalized_due_at,
                priority,
                status,
                normalized_recurrence["recurrence_type"],
                normalized_recurrence["recurrence_interval"],
                normalized_recurrence["recurrence_until"],
                normalized_recurrence["recurrence_count"],
            ),
        )

    def listTasks(self, calendar_id: Optional[int] = None, status: Optional[str] = None):
        """
        Return tasks optionally filtered by calendar and status.
        """

        return self.searchTasks(calendar_id=calendar_id, status=status)

    def searchTasks(
        self,
        query: Optional[str] = None,
        calendar_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
    ):
        """
        Search and filter tasks using text, status, priority, and due-date filters.
        """

        if not self.database:
            return []

        query_value = (query or "").strip().lower()
        status_value = (status or "").strip().lower()
        priority_value = (priority or "").strip().lower()
        query_timezone = self.getCalendarTimezone(calendar_id)
        normalized_due_before = (
            self._normalizeDateTimeValue(
                due_before,
                source_timezone=query_timezone,
                target_timezone=query_timezone,
            )
            if due_before is not None
            else None
        )
        normalized_due_after = (
            self._normalizeDateTimeValue(
                due_after,
                source_timezone=query_timezone,
                target_timezone=query_timezone,
            )
            if due_after is not None
            else None
        )
        rows = self._fetchStoredTasks(calendar_id=calendar_id)
        if normalized_due_before is not None and normalized_due_after is not None:
            rows = self._expandRecurringTasks(rows, normalized_due_after, normalized_due_before)

        filtered = []
        for row in rows:
            title_text = str(row.get("title") or "").lower()
            description_text = str(row.get("description") or "").lower()
            due_at = row.get("due_at")

            if query_value and query_value not in title_text and query_value not in description_text:
                continue
            if status_value and str(row.get("status") or "").lower() != status_value:
                continue
            if priority_value and str(row.get("priority") or "").lower() != priority_value:
                continue
            if normalized_due_before is not None and due_at is not None and due_at > normalized_due_before:
                continue
            if normalized_due_after is not None and due_at is not None and due_at < normalized_due_after:
                continue
            filtered.append(dict(row))

        return filtered

    def getTask(self, task_id: int):
        """
        Return one task by ID.
        """

        if not self.database:
            return None

        row = self.database.fetchOne(
            """
            SELECT id, calendar_id, title, description, due_at, priority, status,
                   linked_event_id, timezone, categories, notification_preferences,
                   recurrence_type, recurrence_interval, recurrence_until, recurrence_count,
                   completed_at, created_at
            FROM calendar_tasks
            WHERE id = ?
            """,
            (task_id,),
        )
        return self._prepareTaskRow(row)

    def updateTask(self, task_id: int, **fields):
        """
        Update one task using a dynamic field map.
        """

        normalized_fields = dict(fields)
        current = self.getTask(task_id) or {}
        task_timezone = normalized_fields.get("timezone", current.get("timezone", "UTC"))
        if "categories" in normalized_fields:
            normalized_fields["categories"] = self._serializeStringList(normalized_fields["categories"])
        if "notification_preferences" in normalized_fields:
            normalized_fields["notification_preferences"] = self._serializeJsonValue(
                normalized_fields["notification_preferences"]
            )

        if normalized_fields.get("due_at") is not None:
            normalized_fields["due_at"] = self._normalizeDateTimeValue(
                normalized_fields["due_at"],
                source_timezone=task_timezone,
            )
        if normalized_fields.get("completed_at") is not None:
            normalized_fields["completed_at"] = self._normalizeDateTimeValue(
                normalized_fields["completed_at"],
                source_timezone=task_timezone,
            )
        if {
            "recurrence_type",
            "recurrence_interval",
            "recurrence_until",
            "recurrence_count",
        }.intersection(normalized_fields):
            normalized_fields.update(
                self._normalizeRecurrence(
                    recurrence_type=normalized_fields.get("recurrence_type", current.get("recurrence_type")),
                    recurrence_interval=normalized_fields.get(
                        "recurrence_interval",
                        current.get("recurrence_interval", 1),
                    ),
                    recurrence_until=normalized_fields.get(
                        "recurrence_until",
                        current.get("recurrence_until"),
                    ),
                    recurrence_count=normalized_fields.get(
                        "recurrence_count",
                        current.get("recurrence_count"),
                    ),
                    source_timezone=task_timezone,
                )
            )

        self._updateRow(
            table_name="calendar_tasks",
            row_id=task_id,
            fields=normalized_fields,
            allowed_fields={
                "calendar_id",
                "linked_event_id",
                "title",
                "description",
                "timezone",
                "categories",
                "notification_preferences",
                "due_at",
                "priority",
                "status",
                "recurrence_type",
                "recurrence_interval",
                "recurrence_until",
                "recurrence_count",
                "completed_at",
            },
            datetime_fields=set(),
        )

    def deleteTask(self, task_id: int):
        """
        Delete one task and any attached calendar reminders.
        """

        if not self.database:
            return

        self.database.execute("DELETE FROM calendar_task_exceptions WHERE task_id = ?", (task_id,))
        self.database.execute("DELETE FROM calendar_reminders WHERE task_id = ?", (task_id,))
        self.database.execute("DELETE FROM calendar_tasks WHERE id = ?", (task_id,))

    def createTaskRecurrenceException(
        self,
        task_id: int,
        occurrence_due_at: str,
        exception_type: str = "override",
        **overrides,
    ):
        """Create a recurrence exception for one task instance."""

        if not self.database:
            return

        task = self.getTask(task_id)
        if task is None:
            raise ValueError("Task does not exist.")

        task_timezone = str(task.get("timezone") or "UTC")
        normalized_occurrence_due_at = self._normalizeDateTimeValue(
            occurrence_due_at,
            source_timezone=task_timezone,
        )
        normalized_type = str(exception_type).strip().lower()
        if normalized_type not in {"cancel", "override"}:
            raise ValueError("Invalid exception type. Use cancel or override.")

        self.database.execute(
            """
            INSERT INTO calendar_task_exceptions (
                task_id, occurrence_due_at, exception_type, override_title,
                override_description, override_due_at, override_priority,
                override_status, override_categories, override_notification_preferences
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(task_id),
                normalized_occurrence_due_at,
                normalized_type,
                overrides.get("title"),
                overrides.get("description"),
                self._normalizeDateTimeValue(
                    overrides["due_at"],
                    source_timezone=task_timezone,
                )
                if overrides.get("due_at") is not None
                else None,
                overrides.get("priority"),
                overrides.get("status"),
                self._serializeStringList(overrides.get("categories"))
                if "categories" in overrides
                else None,
                self._serializeJsonValue(overrides.get("notification_preferences"))
                if "notification_preferences" in overrides
                else None,
            ),
        )

    def cancelTaskOccurrence(self, task_id: int, occurrence_due_at: str):
        """Cancel one recurring task instance."""

        self.createTaskRecurrenceException(
            task_id=task_id,
            occurrence_due_at=occurrence_due_at,
            exception_type="cancel",
        )

    def updateTaskOccurrence(self, task_id: int, occurrence_due_at: str, **overrides):
        """Override one recurring task instance."""

        self.createTaskRecurrenceException(
            task_id=task_id,
            occurrence_due_at=occurrence_due_at,
            exception_type="override",
            **overrides,
        )

    def updateTaskSeries(
        self,
        task_id: int,
        scope: str = "all",
        occurrence_due_at: Optional[str] = None,
        **fields,
    ):
        """Update a recurring task using one/following/all scope."""

        normalized_scope = str(scope).strip().lower()
        if normalized_scope == "all":
            self.updateTask(task_id, **fields)
            return
        if normalized_scope == "one":
            if occurrence_due_at is None:
                raise ValueError("occurrence_due_at is required for one-instance updates.")
            self.updateTaskOccurrence(task_id, occurrence_due_at, **fields)
            return
        if normalized_scope != "following":
            raise ValueError("Invalid scope. Use one, following, or all.")

        self._splitTaskSeries(task_id, occurrence_due_at, fields)

    def deleteTaskSeries(self, task_id: int, scope: str = "all", occurrence_due_at: Optional[str] = None):
        """Delete a recurring task using one/all scope."""

        normalized_scope = str(scope).strip().lower()
        if normalized_scope == "all":
            self.deleteTask(task_id)
            return
        if normalized_scope == "one":
            if occurrence_due_at is None:
                raise ValueError("occurrence_due_at is required for one-instance deletes.")
            self.cancelTaskOccurrence(task_id, occurrence_due_at)
            return
        if normalized_scope != "following":
            raise ValueError("Invalid scope. Use one, following, or all.")

        self._splitTaskSeries(task_id, occurrence_due_at, None)

    def createReminder(
        self,
        title: str,
        remind_at: str,
        calendar_id: Optional[int] = None,
        event_id: Optional[int] = None,
        task_id: Optional[int] = None,
        notes: Optional[str] = None,
        timezone: Optional[str] = None,
        notification_preferences: Optional[dict] = None,
        recurrence_type: Optional[str] = None,
        recurrence_interval: int = 1,
        recurrence_until: Optional[str] = None,
        recurrence_count: Optional[int] = None,
    ):
        """
        Create a calendar reminder entry.
        """

        if not self.database:
            return

        resolved_calendar_id = self._resolveCalendarId(calendar_id)
        reminder_timezone = timezone or self.getCalendarTimezone(resolved_calendar_id)
        normalized_remind_at = self._normalizeDateTimeValue(
            remind_at,
            source_timezone=reminder_timezone,
        )
        normalized_recurrence = self._normalizeRecurrence(
            recurrence_type=recurrence_type,
            recurrence_interval=recurrence_interval,
            recurrence_until=recurrence_until,
            recurrence_count=recurrence_count,
            source_timezone=reminder_timezone,
        )

        cursor = self.database.execute(
            """
            INSERT INTO calendar_reminders (
                calendar_id, event_id, task_id, title, notes, timezone, notification_preferences,
                remind_at, recurrence_type, recurrence_interval, recurrence_until, recurrence_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resolved_calendar_id,
                event_id,
                task_id,
                title,
                notes,
                reminder_timezone,
                self._serializeJsonValue(notification_preferences),
                normalized_remind_at,
                normalized_recurrence["recurrence_type"],
                normalized_recurrence["recurrence_interval"],
                normalized_recurrence["recurrence_until"],
                normalized_recurrence["recurrence_count"],
            ),
        )
        reminder_id = self._resolveInsertedRowId(cursor, "calendar_reminders")
        self._queueReminderForEvent(
            event_id=event_id,
            title=title,
            content=notes,
            remind_at=normalized_remind_at,
            timezone=reminder_timezone,
            recurrence_type=normalized_recurrence["recurrence_type"],
        )
        return reminder_id

    def listReminders(self, calendar_id: Optional[int] = None, include_delivered: bool = True):
        """
        Return calendar reminders optionally filtered by calendar and delivery state.
        """

        return self.searchReminders(calendar_id=calendar_id, include_delivered=include_delivered)

    def searchReminders(
        self,
        query: Optional[str] = None,
        calendar_id: Optional[int] = None,
        event_id: Optional[int] = None,
        task_id: Optional[int] = None,
        include_delivered: bool = True,
        remind_before: Optional[str] = None,
        remind_after: Optional[str] = None,
    ):
        """
        Search and filter calendar reminders.
        """

        if not self.database:
            return []

        query_value = (query or "").strip().lower()
        query_timezone = self.getCalendarTimezone(calendar_id)
        normalized_remind_before = (
            self._normalizeDateTimeValue(
                remind_before,
                source_timezone=query_timezone,
                target_timezone=query_timezone,
            )
            if remind_before is not None
            else None
        )
        normalized_remind_after = (
            self._normalizeDateTimeValue(
                remind_after,
                source_timezone=query_timezone,
                target_timezone=query_timezone,
            )
            if remind_after is not None
            else None
        )
        rows = self._fetchStoredReminders(calendar_id=calendar_id)
        if normalized_remind_before is not None and normalized_remind_after is not None:
            rows = self._expandRecurringReminders(rows, normalized_remind_after, normalized_remind_before)

        filtered = []
        for row in rows:
            title_text = str(row.get("title") or "").lower()
            notes_text = str(row.get("notes") or "").lower()
            remind_at = row.get("remind_at")

            if event_id is not None and row.get("event_id") != event_id:
                continue
            if task_id is not None and row.get("task_id") != task_id:
                continue
            if not include_delivered and row.get("delivered_at") is not None:
                continue
            if query_value and query_value not in title_text and query_value not in notes_text:
                continue
            if normalized_remind_before is not None and remind_at is not None and remind_at > normalized_remind_before:
                continue
            if normalized_remind_after is not None and remind_at is not None and remind_at < normalized_remind_after:
                continue
            filtered.append(dict(row))

        return filtered

    def updateReminder(self, reminder_id: int, **fields):
        """
        Update one reminder using a dynamic field map.
        """

        normalized_fields = dict(fields)
        current = self.getReminder(reminder_id) or {}
        reminder_timezone = normalized_fields.get("timezone", current.get("timezone", "UTC"))
        if "notification_preferences" in normalized_fields:
            normalized_fields["notification_preferences"] = self._serializeJsonValue(
                normalized_fields["notification_preferences"]
            )

        if normalized_fields.get("remind_at") is not None:
            normalized_fields["remind_at"] = self._normalizeDateTimeValue(
                normalized_fields["remind_at"],
                source_timezone=reminder_timezone,
            )
        if normalized_fields.get("delivered_at") is not None:
            normalized_fields["delivered_at"] = self._normalizeDateTimeValue(
                normalized_fields["delivered_at"],
                source_timezone=reminder_timezone,
            )
        if {
            "recurrence_type",
            "recurrence_interval",
            "recurrence_until",
            "recurrence_count",
        }.intersection(normalized_fields):
            normalized_fields.update(
                self._normalizeRecurrence(
                    recurrence_type=normalized_fields.get(
                        "recurrence_type",
                        current.get("recurrence_type"),
                    ),
                    recurrence_interval=normalized_fields.get(
                        "recurrence_interval",
                        current.get("recurrence_interval", 1),
                    ),
                    recurrence_until=normalized_fields.get(
                        "recurrence_until",
                        current.get("recurrence_until"),
                    ),
                    recurrence_count=normalized_fields.get(
                        "recurrence_count",
                        current.get("recurrence_count"),
                    ),
                    source_timezone=reminder_timezone,
                )
            )

        self._updateRow(
            table_name="calendar_reminders",
            row_id=reminder_id,
            fields=normalized_fields,
            allowed_fields={
                "calendar_id",
                "event_id",
                "task_id",
                "title",
                "notes",
                "timezone",
                "notification_preferences",
                "remind_at",
                "recurrence_type",
                "recurrence_interval",
                "recurrence_until",
                "recurrence_count",
                "delivered_at",
            },
            datetime_fields=set(),
        )

    def deleteReminder(self, reminder_id: int):
        """
        Delete one calendar reminder.
        """

        if not self.database:
            return

        self.database.execute("DELETE FROM calendar_reminder_exceptions WHERE reminder_id = ?", (reminder_id,))
        self.database.execute("DELETE FROM calendar_reminders WHERE id = ?", (reminder_id,))

    def getReminder(self, reminder_id: int):
        """Return one reminder by ID."""

        if not self.database:
            return None

        row = self.database.fetchOne(
            """
            SELECT id, calendar_id, event_id, task_id, title, notes, timezone,
                   notification_preferences, remind_at, recurrence_type, recurrence_interval,
                   recurrence_until, recurrence_count, delivered_at, created_at
            FROM calendar_reminders
            WHERE id = ?
            """,
            (reminder_id,),
        )
        return self._prepareReminderRow(row)

    def createReminderRecurrenceException(
        self,
        reminder_id: int,
        occurrence_remind_at: str,
        exception_type: str = "override",
        **overrides,
    ):
        """Create a recurrence exception for one reminder instance."""

        if not self.database:
            return

        reminder = self.getReminder(reminder_id)
        if reminder is None:
            raise ValueError("Reminder does not exist.")

        reminder_timezone = str(reminder.get("timezone") or "UTC")
        normalized_occurrence_remind_at = self._normalizeDateTimeValue(
            occurrence_remind_at,
            source_timezone=reminder_timezone,
        )
        normalized_type = str(exception_type).strip().lower()
        if normalized_type not in {"cancel", "override"}:
            raise ValueError("Invalid exception type. Use cancel or override.")

        self.database.execute(
            """
            INSERT INTO calendar_reminder_exceptions (
                reminder_id, occurrence_remind_at, exception_type, override_title,
                override_notes, override_remind_at, override_notification_preferences
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(reminder_id),
                normalized_occurrence_remind_at,
                normalized_type,
                overrides.get("title"),
                overrides.get("notes"),
                self._normalizeDateTimeValue(
                    overrides["remind_at"],
                    source_timezone=reminder_timezone,
                )
                if overrides.get("remind_at") is not None
                else None,
                self._serializeJsonValue(overrides.get("notification_preferences"))
                if "notification_preferences" in overrides
                else None,
            ),
        )

    def cancelReminderOccurrence(self, reminder_id: int, occurrence_remind_at: str):
        """Cancel one recurring reminder instance."""

        self.createReminderRecurrenceException(
            reminder_id=reminder_id,
            occurrence_remind_at=occurrence_remind_at,
            exception_type="cancel",
        )

    def updateReminderOccurrence(self, reminder_id: int, occurrence_remind_at: str, **overrides):
        """Override one recurring reminder instance."""

        self.createReminderRecurrenceException(
            reminder_id=reminder_id,
            occurrence_remind_at=occurrence_remind_at,
            exception_type="override",
            **overrides,
        )

    def updateReminderSeries(
        self,
        reminder_id: int,
        scope: str = "all",
        occurrence_remind_at: Optional[str] = None,
        **fields,
    ):
        """Update a recurring reminder using one/all scope."""

        normalized_scope = str(scope).strip().lower()
        if normalized_scope == "all":
            self.updateReminder(reminder_id, **fields)
            return
        if normalized_scope == "one":
            if occurrence_remind_at is None:
                raise ValueError("occurrence_remind_at is required for one-instance updates.")
            self.updateReminderOccurrence(reminder_id, occurrence_remind_at, **fields)
            return
        if normalized_scope != "following":
            raise ValueError("Invalid scope. Use one, following, or all.")

        self._splitReminderSeries(reminder_id, occurrence_remind_at, fields)

    def deleteReminderSeries(
        self,
        reminder_id: int,
        scope: str = "all",
        occurrence_remind_at: Optional[str] = None,
    ):
        """Delete a recurring reminder using one/all scope."""

        normalized_scope = str(scope).strip().lower()
        if normalized_scope == "all":
            self.deleteReminder(reminder_id)
            return
        if normalized_scope == "one":
            if occurrence_remind_at is None:
                raise ValueError("occurrence_remind_at is required for one-instance deletes.")
            self.cancelReminderOccurrence(reminder_id, occurrence_remind_at)
            return
        if normalized_scope != "following":
            raise ValueError("Invalid scope. Use one, following, or all.")

        self._splitReminderSeries(reminder_id, occurrence_remind_at, None)

    def processDueReminders(self):
        """
        Find due calendar reminders, mark them delivered, and emit events.

        Returns:
            list[dict]:
                Reminder rows emitted during this poll cycle.
        """

        if not self.database:
            return []

        rows = self.database.fetchAll(
            """
            SELECT id, calendar_id, event_id, task_id, title, notes, remind_at,
                   delivered_at, created_at
            FROM calendar_reminders
            WHERE delivered_at IS NULL
              AND remind_at <= NOW()
            ORDER BY remind_at ASC, id ASC
            """
        )

        for row in rows:
            reminder_id = row.get("id")
            self.database.execute(
                """
                UPDATE calendar_reminders
                SET delivered_at = NOW()
                WHERE id = ?
                """,
                (reminder_id,),
            )

            if getattr(self.context, "eventManager", None):
                self.context.eventManager.emit(
                    Event(
                        "calendar_reminder_triggered",
                        {
                            "id": reminder_id,
                            "calendar_id": row.get("calendar_id"),
                            "event_id": row.get("event_id"),
                            "task_id": row.get("task_id"),
                            "title": row.get("title"),
                            "notes": row.get("notes"),
                            "remind_at": row.get("remind_at"),
                            "created_at": row.get("created_at"),
                        },
                    )
                )

        return rows

    def buildDayView(self, day: str, calendar_id: Optional[int] = None) -> Dict[str, object]:
        """
        Return a day-level overview of events, tasks, and reminders.
        """

        normalized_day = self._normalizeDateValue(day)
        day_start = f"{normalized_day} 00:00:00"
        day_end = f"{normalized_day} 23:59:59"

        return {
            "day": normalized_day,
            "events": self.listEventsForRange(day_start, day_end, calendar_id=calendar_id),
            "tasks": self.searchTasks(calendar_id=calendar_id),
            "reminders": self.searchReminders(
                calendar_id=calendar_id,
                remind_after=day_start,
                remind_before=day_end,
            ),
        }

    def listEventsForWeek(self, day: str, calendar_id: Optional[int] = None):
        """
        Return events for the seven-day window containing the provided date.
        """

        normalized_day = self._parseDate(self._normalizeDateValue(day))
        week_start = normalized_day - timedelta(days=normalized_day.weekday())
        week_end = week_start + timedelta(days=6)
        return self.listEventsForRange(
            f"{week_start.strftime('%Y-%m-%d')} 00:00:00",
            f"{week_end.strftime('%Y-%m-%d')} 23:59:59",
            calendar_id=calendar_id,
        )

    def listEventsForMonth(self, month_value: str, calendar_id: Optional[int] = None):
        """
        Return events for the month containing the provided date.
        """

        normalized_day = self._parseDate(self._normalizeDateValue(month_value))
        month_start = normalized_day.replace(day=1)
        month_end_day = month_calendar.monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=month_end_day)
        return self.listEventsForRange(
            f"{month_start.strftime('%Y-%m-%d')} 00:00:00",
            f"{month_end.strftime('%Y-%m-%d')} 23:59:59",
            calendar_id=calendar_id,
        )

    def buildWeekView(self, day: str, calendar_id: Optional[int] = None) -> Dict[str, object]:
        """
        Return a week-level overview of events, tasks, and reminders.
        """

        normalized_day = self._parseDate(self._normalizeDateValue(day))
        week_start = normalized_day - timedelta(days=normalized_day.weekday())
        week_end = week_start + timedelta(days=6)
        start_text = f"{week_start.strftime('%Y-%m-%d')} 00:00:00"
        end_text = f"{week_end.strftime('%Y-%m-%d')} 23:59:59"
        return {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "events": self.listEventsForRange(start_text, end_text, calendar_id=calendar_id),
            "tasks": self.searchTasks(calendar_id=calendar_id, due_after=start_text, due_before=end_text),
            "reminders": self.searchReminders(
                calendar_id=calendar_id,
                remind_after=start_text,
                remind_before=end_text,
            ),
        }

    def buildMonthView(self, month_value: str, calendar_id: Optional[int] = None) -> Dict[str, object]:
        """
        Return a month-level overview of events, tasks, and reminders.
        """

        normalized_day = self._parseDate(self._normalizeDateValue(month_value))
        month_start = normalized_day.replace(day=1)
        month_end_day = month_calendar.monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=month_end_day)
        start_text = f"{month_start.strftime('%Y-%m-%d')} 00:00:00"
        end_text = f"{month_end.strftime('%Y-%m-%d')} 23:59:59"
        return {
            "month": month_start.strftime("%Y-%m"),
            "events": self.listEventsForRange(start_text, end_text, calendar_id=calendar_id),
            "tasks": self.searchTasks(calendar_id=calendar_id, due_after=start_text, due_before=end_text),
            "reminders": self.searchReminders(
                calendar_id=calendar_id,
                remind_after=start_text,
                remind_before=end_text,
            ),
        }

    def detectConflicts(
        self,
        start_at: str,
        end_at: str,
        calendar_id: Optional[int] = None,
        exclude_event_id: Optional[int] = None,
    ):
        """
        Return overlapping events for an optional conflict check.

        This is informational only. It does not prevent overlapping events.
        """

        rows = self.listEventsForRange(start_at, end_at, calendar_id=calendar_id)
        if exclude_event_id is not None:
            rows = [row for row in rows if int(row.get("id")) != int(exclude_event_id)]
        return rows

    def updateEventSeries(
        self,
        event_id: int,
        scope: str = "all",
        occurrence_start: Optional[str] = None,
        **fields,
    ):
        """
        Update a recurring series using `one`, `following`, or `all` scope.
        """

        normalized_scope = str(scope).strip().lower()
        if normalized_scope == "all":
            self.updateEvent(event_id, **fields)
            return
        if normalized_scope == "one":
            if occurrence_start is None:
                raise ValueError("occurrence_start is required for one-instance updates.")
            self.updateOccurrence(event_id, occurrence_start, **fields)
            return
        if normalized_scope != "following":
            raise ValueError("Invalid scope. Use one, following, or all.")

        self._splitEventSeries(event_id, occurrence_start, fields)

    def deleteEventSeries(
        self,
        event_id: int,
        scope: str = "all",
        occurrence_start: Optional[str] = None,
    ):
        """
        Delete a recurring series using `one`, `following`, or `all` scope.
        """

        normalized_scope = str(scope).strip().lower()
        if normalized_scope == "all":
            self.deleteEvent(event_id)
            return
        if normalized_scope == "one":
            if occurrence_start is None:
                raise ValueError("occurrence_start is required for one-instance deletes.")
            self.cancelOccurrence(event_id, occurrence_start)
            return
        if normalized_scope != "following":
            raise ValueError("Invalid scope. Use one, following, or all.")

        self._splitEventSeries(event_id, occurrence_start, None)

    def _splitEventSeries(self, event_id: int, occurrence_start: Optional[str], fields: Optional[dict]):
        """Split a recurring series at one occurrence and optionally create a new following series."""

        if occurrence_start is None:
            raise ValueError("occurrence_start is required for following-scope series edits.")

        event = self.getEvent(event_id)
        if event is None:
            raise ValueError("Event does not exist.")
        if not event.get("recurrence_type"):
            if fields:
                self.updateEvent(event_id, **fields)
            return

        event_timezone = str(event.get("timezone") or "UTC")
        normalized_occurrence_start = self._normalizeDateTimeValue(
            occurrence_start,
            allow_date_only=bool(event.get("all_day")),
            source_timezone=event_timezone,
            target_timezone=event_timezone,
        )
        previous_start = self._advanceOccurrence(
            self._parseDateTime(normalized_occurrence_start),
            event["recurrence_type"],
            -int(event.get("recurrence_interval") or 1),
        )
        self.updateEvent(
            event_id,
            recurrence_until=previous_start.strftime("%Y-%m-%d %H:%M:%S"),
        )

        if fields is None:
            return

        cloned_fields = {
            "title": fields.get("title", event.get("title")),
            "start_at": fields.get("start_at", normalized_occurrence_start),
            "end_at": fields.get("end_at", event.get("end_at")),
            "calendar_id": fields.get("calendar_id", event.get("calendar_id")),
            "description": fields.get("description", event.get("description")),
            "location": fields.get("location", event.get("location")),
            "attendees": fields.get("attendees", event.get("attendees")),
            "organizer": fields.get("organizer", event.get("organizer")),
            "timezone": fields.get("timezone", event.get("timezone")),
            "visibility": fields.get("visibility", event.get("visibility")),
            "categories": fields.get("categories", event.get("categories")),
            "notification_preferences": fields.get(
                "notification_preferences",
                event.get("notification_preferences"),
            ),
            "linked_task_id": fields.get("linked_task_id", event.get("linked_task_id")),
            "all_day": fields.get("all_day", event.get("all_day")),
            "status": fields.get("status", event.get("status")),
            "recurrence_type": fields.get("recurrence_type", event.get("recurrence_type")),
            "recurrence_interval": fields.get(
                "recurrence_interval",
                event.get("recurrence_interval", 1),
            ),
            "recurrence_until": fields.get("recurrence_until", event.get("recurrence_until")),
            "recurrence_count": fields.get("recurrence_count", event.get("recurrence_count")),
        }
        self.createEvent(**cloned_fields)

    def _splitTaskSeries(self, task_id: int, occurrence_due_at: Optional[str], fields: Optional[dict]):
        """Split a recurring task series at one occurrence and optionally create a new following series."""

        if occurrence_due_at is None:
            raise ValueError("occurrence_due_at is required for following-scope series edits.")

        task = self.getTask(task_id)
        if task is None:
            raise ValueError("Task does not exist.")
        if not task.get("recurrence_type"):
            if fields:
                self.updateTask(task_id, **fields)
            return

        task_timezone = str(task.get("timezone") or "UTC")
        normalized_occurrence_due_at = self._normalizeDateTimeValue(
            occurrence_due_at,
            source_timezone=task_timezone,
            target_timezone=task_timezone,
        )
        previous_due_at = self._advanceOccurrence(
            self._parseDateTime(normalized_occurrence_due_at),
            task["recurrence_type"],
            -int(task.get("recurrence_interval") or 1),
        )
        self.updateTask(
            task_id,
            recurrence_until=previous_due_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        if fields is None:
            return

        cloned_fields = {
            "title": fields.get("title", task.get("title")),
            "due_at": fields.get("due_at", normalized_occurrence_due_at),
            "calendar_id": fields.get("calendar_id", task.get("calendar_id")),
            "linked_event_id": fields.get("linked_event_id", task.get("linked_event_id")),
            "description": fields.get("description", task.get("description")),
            "timezone": fields.get("timezone", task.get("timezone")),
            "categories": fields.get("categories", task.get("categories")),
            "notification_preferences": fields.get(
                "notification_preferences",
                task.get("notification_preferences"),
            ),
            "priority": fields.get("priority", task.get("priority")),
            "status": fields.get("status", task.get("status")),
            "recurrence_type": fields.get("recurrence_type", task.get("recurrence_type")),
            "recurrence_interval": fields.get(
                "recurrence_interval",
                task.get("recurrence_interval", 1),
            ),
            "recurrence_until": fields.get("recurrence_until", task.get("recurrence_until")),
            "recurrence_count": fields.get("recurrence_count", task.get("recurrence_count")),
        }
        self.createTask(**cloned_fields)

    def _splitReminderSeries(
        self,
        reminder_id: int,
        occurrence_remind_at: Optional[str],
        fields: Optional[dict],
    ):
        """Split a recurring reminder series at one occurrence and optionally create a new following series."""

        if occurrence_remind_at is None:
            raise ValueError("occurrence_remind_at is required for following-scope series edits.")

        reminder = self.getReminder(reminder_id)
        if reminder is None:
            raise ValueError("Reminder does not exist.")
        if not reminder.get("recurrence_type"):
            if fields:
                self.updateReminder(reminder_id, **fields)
            return

        reminder_timezone = str(reminder.get("timezone") or "UTC")
        normalized_occurrence_remind_at = self._normalizeDateTimeValue(
            occurrence_remind_at,
            source_timezone=reminder_timezone,
            target_timezone=reminder_timezone,
        )
        previous_remind_at = self._advanceOccurrence(
            self._parseDateTime(normalized_occurrence_remind_at),
            reminder["recurrence_type"],
            -int(reminder.get("recurrence_interval") or 1),
        )
        self.updateReminder(
            reminder_id,
            recurrence_until=previous_remind_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        if fields is None:
            return

        cloned_fields = {
            "title": fields.get("title", reminder.get("title")),
            "remind_at": fields.get("remind_at", normalized_occurrence_remind_at),
            "calendar_id": fields.get("calendar_id", reminder.get("calendar_id")),
            "event_id": fields.get("event_id", reminder.get("event_id")),
            "task_id": fields.get("task_id", reminder.get("task_id")),
            "notes": fields.get("notes", reminder.get("notes")),
            "timezone": fields.get("timezone", reminder.get("timezone")),
            "notification_preferences": fields.get(
                "notification_preferences",
                reminder.get("notification_preferences"),
            ),
            "recurrence_type": fields.get("recurrence_type", reminder.get("recurrence_type")),
            "recurrence_interval": fields.get(
                "recurrence_interval",
                reminder.get("recurrence_interval", 1),
            ),
            "recurrence_until": fields.get("recurrence_until", reminder.get("recurrence_until")),
            "recurrence_count": fields.get("recurrence_count", reminder.get("recurrence_count")),
        }
        self.createReminder(**cloned_fields)

    def _queueEventRemindersFromPreferences(
        self,
        event_id: Optional[int],
        title: str,
        description: Optional[str],
        start_at: str,
        timezone: str,
        notification_preferences: Optional[dict],
    ):
        """
        Queue event reminders through the shared reminders module.

        Supported preference keys:
        - `reminders`: list of explicit reminder datetimes
        - `reminder_timestamps`: alias for explicit reminder datetimes
        - `minutes_before`: list of integer minute offsets before the event
        """

        if event_id is None or not isinstance(notification_preferences, dict):
            return

        explicit_values = list(notification_preferences.get("reminders") or [])
        explicit_values.extend(list(notification_preferences.get("reminder_timestamps") or []))
        minutes_before = list(notification_preferences.get("minutes_before") or [])

        for reminder_value in explicit_values:
            self._queueReminderForEvent(
                event_id=event_id,
                title=title,
                content=description,
                remind_at=str(reminder_value),
                timezone=timezone,
            )

        for offset_minutes in minutes_before:
            try:
                minutes_value = int(offset_minutes)
            except (TypeError, ValueError):
                continue

            reminder_time = self._buildReminderTimeBeforeEvent(
                start_at=start_at,
                timezone=timezone,
                minutes_before=minutes_value,
            )
            self._queueReminderForEvent(
                event_id=event_id,
                title=title,
                content=description,
                remind_at=reminder_time,
                timezone=timezone,
            )

    def _queueReminderForEvent(
        self,
        event_id: Optional[int],
        title: str,
        content: Optional[str],
        remind_at: str,
        timezone: str,
        recurrence_type: Optional[str] = None,
    ):
        """
        Mirror one event reminder into the shared reminders module.

        Only single-instance reminders are mirrored on `master`. Recurring
        calendar reminders remain owned by the calendar module.
        """

        if event_id is None or recurrence_type:
            return

        reminders = getattr(self.context, "reminders", None)
        if reminders is None:
            return

        reminder_display_time = remind_at
        if "-" in str(remind_at) and ":" in str(remind_at):
            reminder_display_time = self.context.dtUtil.toPreferredDateTime(
                self._convertStoredDateTimeToDisplay(remind_at, timezone)
            )

        reminders.createReminder(
            title=str(title),
            content=str(content or title),
            module_of_origin=f"calendar:event:{int(event_id)}",
            reminder_at=reminder_display_time,
        )

    def _buildReminderTimeBeforeEvent(self, start_at: str, timezone: str, minutes_before: int) -> str:
        """
        Build a reminder datetime by subtracting minutes from an event start.
        """

        display_start = self._convertStoredDateTimeToDisplay(start_at, timezone)
        event_start = self._parseDateTime(str(display_start))
        reminder_time = event_start - timedelta(minutes=int(minutes_before))
        return reminder_time.strftime("%Y-%m-%d %H:%M:%S")

    def _resolveInsertedRowId(self, cursor, table_name: str) -> Optional[int]:
        """
        Return the inserted row ID using cursor metadata or a simple fallback query.
        """

        last_row_id = getattr(cursor, "lastrowid", None)
        if last_row_id is not None:
            return int(last_row_id)

        row = self.database.fetchOne(
            f"""
            SELECT id
            FROM {table_name}
            ORDER BY id DESC
            LIMIT 1
            """
        )
        if row is None:
            return None
        return int(row["id"])

    def _resolveCalendarId(self, calendar_id: Optional[int]) -> int:
        """
        Resolve an explicit or default calendar ID.
        """

        if calendar_id is not None:
            return int(calendar_id)

        default_calendar_id = self.getDefaultCalendarId()
        if default_calendar_id is None:
            raise RuntimeError("No default calendar exists.")
        return default_calendar_id

    def getCalendar(self, calendar_id: int):
        """Return one calendar container by ID."""

        if not self.database:
            return None

        return self.database.fetchOne(
            """
            SELECT id, name, description, color, timezone, visibility, is_default, created_at
            FROM calendar_calendars
            WHERE id = ?
            """,
            (int(calendar_id),),
        )

    def getCalendarTimezone(self, calendar_id: Optional[int] = None) -> str:
        """Return the configured timezone for a calendar, defaulting to UTC."""

        resolved_calendar_id = self._resolveCalendarId(calendar_id)
        row = self.getCalendar(resolved_calendar_id)
        if row and row.get("timezone"):
            return str(row["timezone"])
        return "UTC"

    def convertDateTimeBetweenTimezones(
        self,
        value: str,
        from_timezone: str,
        to_timezone: str,
    ) -> str:
        """
        Convert a normalized datetime string between timezones.
        """

        return self._normalizeDateTimeValue(
            value,
            source_timezone=from_timezone,
            target_timezone=to_timezone,
        )

    def _fetchStoredEvents(self, calendar_id: Optional[int] = None):
        """
        Fetch stored event rows and normalize backend-only fields.
        """

        if not self.database:
            return []

        query = """
            SELECT id, calendar_id, title, description, location, attendees, start_at, end_at,
                   organizer, timezone, visibility, categories, notification_preferences,
                   linked_task_id, all_day, status, recurrence_type, recurrence_interval,
                   recurrence_until, recurrence_count, created_at
            FROM calendar_events
        """
        params = ()
        if calendar_id is not None:
            query += " WHERE calendar_id = ?"
            params = (int(calendar_id),)

        query += " ORDER BY start_at ASC, id ASC"
        return [self._prepareEventRow(row) for row in self.database.fetchAll(query, params)]

    def _fetchStoredTasks(self, calendar_id: Optional[int] = None):
        """Fetch stored task rows and normalize backend-only fields."""

        if not self.database:
            return []

        query = """
            SELECT id, calendar_id, linked_event_id, title, description, timezone, categories,
                   notification_preferences, due_at, priority, status, recurrence_type,
                   recurrence_interval, recurrence_until, recurrence_count, completed_at, created_at
            FROM calendar_tasks
        """
        params = ()
        if calendar_id is not None:
            query += " WHERE calendar_id = ?"
            params = (int(calendar_id),)

        query += " ORDER BY due_at ASC, id ASC"
        return [self._prepareTaskRow(row) for row in self.database.fetchAll(query, params)]

    def _fetchStoredReminders(self, calendar_id: Optional[int] = None):
        """Fetch stored reminder rows and normalize backend-only fields."""

        if not self.database:
            return []

        query = """
            SELECT id, calendar_id, event_id, task_id, title, notes, timezone,
                   notification_preferences, remind_at, recurrence_type, recurrence_interval,
                   recurrence_until, recurrence_count, delivered_at, created_at
            FROM calendar_reminders
        """
        params = ()
        if calendar_id is not None:
            query += " WHERE calendar_id = ?"
            params = (int(calendar_id),)

        query += " ORDER BY remind_at ASC, id ASC"
        return [self._prepareReminderRow(row) for row in self.database.fetchAll(query, params)]

    def _fetchEventExceptions(self, event_id: int, event_timezone: str) -> dict[str, dict]:
        """
        Return recurrence exceptions indexed by occurrence start datetime string.
        """

        if not self.database:
            return {}

        rows = self.database.fetchAll(
            """
            SELECT id, event_id, occurrence_start, exception_type, override_title,
                   override_description, override_location, override_attendees,
                   override_start_at, override_end_at, override_all_day, override_status,
                   created_at
            FROM calendar_event_exceptions
            WHERE event_id = ?
            ORDER BY occurrence_start ASC, id ASC
            """,
            (int(event_id),),
        )

        indexed = {}
        for row in rows:
            prepared = dict(row)
            prepared["override_attendees"] = self._deserializeAttendees(
                prepared.get("override_attendees")
            )
            prepared["occurrence_start"] = self._convertStoredDateTimeToDisplay(
                prepared.get("occurrence_start"),
                event_timezone,
            )
            prepared["override_start_at"] = self._convertStoredDateTimeToDisplay(
                prepared.get("override_start_at"),
                event_timezone,
            )
            prepared["override_end_at"] = self._convertStoredDateTimeToDisplay(
                prepared.get("override_end_at"),
                event_timezone,
            )
            indexed[str(prepared["occurrence_start"])] = prepared
        return indexed

    def _fetchTaskExceptions(self, task_id: int, task_timezone: str) -> dict[str, dict]:
        """Return task recurrence exceptions indexed by displayed due datetime."""

        if not self.database:
            return {}

        rows = self.database.fetchAll(
            """
            SELECT id, task_id, occurrence_due_at, exception_type, override_title,
                   override_description, override_due_at, override_priority,
                   override_status, override_categories, override_notification_preferences,
                   created_at
            FROM calendar_task_exceptions
            WHERE task_id = ?
            ORDER BY occurrence_due_at ASC, id ASC
            """,
            (int(task_id),),
        )

        indexed = {}
        for row in rows:
            prepared = dict(row)
            prepared["override_categories"] = self._deserializeStringList(
                prepared.get("override_categories")
            )
            prepared["override_notification_preferences"] = self._deserializeJsonValue(
                prepared.get("override_notification_preferences")
            )
            prepared["occurrence_due_at"] = self._convertStoredDateTimeToDisplay(
                prepared.get("occurrence_due_at"),
                task_timezone,
            )
            prepared["override_due_at"] = self._convertStoredDateTimeToDisplay(
                prepared.get("override_due_at"),
                task_timezone,
            )
            indexed[str(prepared["occurrence_due_at"])] = prepared
        return indexed

    def _fetchReminderExceptions(self, reminder_id: int, reminder_timezone: str) -> dict[str, dict]:
        """Return reminder recurrence exceptions indexed by displayed reminder datetime."""

        if not self.database:
            return {}

        rows = self.database.fetchAll(
            """
            SELECT id, reminder_id, occurrence_remind_at, exception_type, override_title,
                   override_notes, override_remind_at, override_notification_preferences,
                   created_at
            FROM calendar_reminder_exceptions
            WHERE reminder_id = ?
            ORDER BY occurrence_remind_at ASC, id ASC
            """,
            (int(reminder_id),),
        )

        indexed = {}
        for row in rows:
            prepared = dict(row)
            prepared["override_notification_preferences"] = self._deserializeJsonValue(
                prepared.get("override_notification_preferences")
            )
            prepared["occurrence_remind_at"] = self._convertStoredDateTimeToDisplay(
                prepared.get("occurrence_remind_at"),
                reminder_timezone,
            )
            prepared["override_remind_at"] = self._convertStoredDateTimeToDisplay(
                prepared.get("override_remind_at"),
                reminder_timezone,
            )
            indexed[str(prepared["occurrence_remind_at"])] = prepared
        return indexed

    def _prepareEventRow(self, row):
        """
        Normalize one stored event row into the public event shape.
        """

        if row is None:
            return None

        prepared = dict(row)
        prepared["attendees"] = self._deserializeAttendees(prepared.get("attendees"))
        prepared["categories"] = self._deserializeStringList(prepared.get("categories"))
        prepared["notification_preferences"] = self._deserializeJsonValue(
            prepared.get("notification_preferences")
        )
        event_timezone = str(prepared.get("timezone") or "UTC")
        for key in ("start_at", "end_at", "recurrence_until"):
            prepared[key] = self._convertStoredDateTimeToDisplay(prepared.get(key), event_timezone)
        prepared["recurrence_interval"] = int(prepared.get("recurrence_interval") or 1)
        prepared["recurrence_count"] = (
            int(prepared["recurrence_count"])
            if prepared.get("recurrence_count") is not None
            else None
        )
        return prepared

    def _prepareTaskRow(self, row):
        """Normalize one stored task row into the public task shape."""

        if row is None:
            return None

        prepared = dict(row)
        prepared["categories"] = self._deserializeStringList(prepared.get("categories"))
        prepared["notification_preferences"] = self._deserializeJsonValue(
            prepared.get("notification_preferences")
        )
        task_timezone = str(prepared.get("timezone") or "UTC")
        for key in ("due_at", "completed_at", "recurrence_until"):
            prepared[key] = self._convertStoredDateTimeToDisplay(prepared.get(key), task_timezone)
        prepared["recurrence_interval"] = int(prepared.get("recurrence_interval") or 1)
        prepared["recurrence_count"] = (
            int(prepared["recurrence_count"])
            if prepared.get("recurrence_count") is not None
            else None
        )
        return prepared

    def _prepareReminderRow(self, row):
        """Normalize one stored reminder row into the public reminder shape."""

        if row is None:
            return None

        prepared = dict(row)
        prepared["notification_preferences"] = self._deserializeJsonValue(
            prepared.get("notification_preferences")
        )
        reminder_timezone = str(prepared.get("timezone") or "UTC")
        for key in ("remind_at", "delivered_at", "recurrence_until"):
            prepared[key] = self._convertStoredDateTimeToDisplay(prepared.get(key), reminder_timezone)
        prepared["recurrence_interval"] = int(prepared.get("recurrence_interval") or 1)
        prepared["recurrence_count"] = (
            int(prepared["recurrence_count"])
            if prepared.get("recurrence_count") is not None
            else None
        )
        return prepared

    def _serializeAttendees(self, attendees: Optional[Iterable[str] | str]) -> str:
        """
        Convert attendees input into a JSON string for storage.
        """

        if attendees is None:
            return "[]"

        if isinstance(attendees, str):
            values = [value.strip() for value in attendees.split(",") if value.strip()]
        else:
            values = [str(value).strip() for value in attendees if str(value).strip()]

        return json.dumps(values)

    def _deserializeAttendees(self, attendees_value) -> list[str]:
        """
        Convert stored attendees data into a normalized list.
        """

        if attendees_value in (None, ""):
            return []

        if isinstance(attendees_value, list):
            return [str(value) for value in attendees_value]

        try:
            parsed = json.loads(attendees_value)
            if isinstance(parsed, list):
                return [str(value) for value in parsed]
        except Exception:
            pass

        return [value.strip() for value in str(attendees_value).split(",") if value.strip()]

    def _serializeStringList(self, values: Optional[Iterable[str] | str]) -> str:
        """Convert string-list input into a JSON string for storage."""

        if values is None:
            return "[]"
        if isinstance(values, str):
            items = [value.strip() for value in values.split(",") if value.strip()]
        else:
            items = [str(value).strip() for value in values if str(value).strip()]
        return json.dumps(items)

    def _deserializeStringList(self, raw_value) -> list[str]:
        """Convert stored list-like values into a normalized string list."""

        if raw_value in (None, ""):
            return []
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [str(value) for value in parsed]
        except Exception:
            pass
        return [value.strip() for value in str(raw_value).split(",") if value.strip()]

    @staticmethod
    def _serializeJsonValue(value) -> Optional[str]:
        """Convert an object to JSON for storage."""

        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def _deserializeJsonValue(raw_value):
        """Convert stored JSON text into a Python object."""

        if raw_value in (None, ""):
            return None
        try:
            return json.loads(raw_value)
        except Exception:
            return raw_value

    def _normalizeRecurrence(
        self,
        recurrence_type: Optional[str],
        recurrence_interval: int,
        recurrence_until: Optional[str],
        recurrence_count: Optional[int],
        source_timezone: str = "UTC",
        allow_date_only: bool = False,
    ) -> dict:
        """
        Validate and normalize recurrence fields for storage.
        """

        if recurrence_type is None or str(recurrence_type).strip() == "":
            return {
                "recurrence_type": None,
                "recurrence_interval": 1,
                "recurrence_until": None,
                "recurrence_count": None,
            }

        normalized_type = str(recurrence_type).strip().lower()
        if normalized_type not in RECURRENCE_TYPES:
            raise ValueError("Invalid recurrence type. Use daily, weekly, monthly, or yearly.")

        normalized_interval = int(recurrence_interval or 1)
        if normalized_interval < 1:
            raise ValueError("Recurrence interval must be at least 1.")

        normalized_until = (
            self._normalizeDateTimeValue(
                recurrence_until,
                allow_date_only=allow_date_only,
                source_timezone=source_timezone,
            )
            if recurrence_until not in (None, "")
            else None
        )
        normalized_count = int(recurrence_count) if recurrence_count not in (None, "") else None
        if normalized_count is not None and normalized_count < 1:
            raise ValueError("Recurrence count must be at least 1.")

        return {
            "recurrence_type": normalized_type,
            "recurrence_interval": normalized_interval,
            "recurrence_until": normalized_until,
            "recurrence_count": normalized_count,
        }

    def _expandRecurringEvent(self, row, range_start: datetime, range_end: datetime):
        """
        Expand one stored recurring event into concrete occurrences.
        """

        base_start = self._parseDateTime(row["start_at"])
        base_end = self._parseDateTime(row["end_at"]) if row.get("end_at") else None
        duration = (base_end - base_start) if base_end is not None else timedelta(0)

        until = self._parseDateTime(row["recurrence_until"]) if row.get("recurrence_until") else None
        count_limit = row.get("recurrence_count")
        interval = int(row.get("recurrence_interval") or 1)

        occurrences = []
        occurrence_start = base_start
        occurrence_index = 0
        exceptions = self._fetchEventExceptions(int(row["id"]), str(row.get("timezone") or "UTC"))

        while occurrence_start <= range_end:
            occurrence_index += 1

            if count_limit is not None and occurrence_index > count_limit:
                break
            if until is not None and occurrence_start > until:
                break

            occurrence_end = (
                occurrence_start + duration if row.get("end_at") is not None else None
            )

            candidate = dict(row)
            candidate["series_id"] = row.get("id")
            candidate["occurrence_index"] = occurrence_index
            candidate["start_at"] = occurrence_start.strftime("%Y-%m-%d %H:%M:%S")
            candidate["end_at"] = (
                occurrence_end.strftime("%Y-%m-%d %H:%M:%S")
                if occurrence_end is not None
                else None
            )
            candidate["is_recurring_instance"] = True
            occurrence_key = candidate["start_at"]
            exception = exceptions.get(occurrence_key)

            if exception is not None:
                if exception.get("exception_type") == "cancel":
                    occurrence_start = self._advanceOccurrence(
                        occurrence_start,
                        row.get("recurrence_type"),
                        interval,
                    )
                    continue

                candidate = self._applyOccurrenceOverride(candidate, exception)

            if self._eventOverlapsRange(candidate, range_start, range_end):
                occurrences.append(candidate)

            occurrence_start = self._advanceOccurrence(
                occurrence_start,
                row.get("recurrence_type"),
                interval,
            )

        return occurrences

    def _expandRecurringTasks(self, rows, range_start_text: str, range_end_text: str):
        """Expand recurring tasks into concrete due instances for a date range."""

        range_start = self._parseDateTime(range_start_text)
        range_end = self._parseDateTime(range_end_text)
        expanded = []

        for row in rows:
            if not row.get("recurrence_type"):
                expanded.append(row)
                continue

            base_due = self._parseDateTime(row["due_at"]) if row.get("due_at") else None
            if base_due is None:
                expanded.append(row)
                continue

            until = self._parseDateTime(row["recurrence_until"]) if row.get("recurrence_until") else None
            count_limit = row.get("recurrence_count")
            occurrence_due = base_due
            occurrence_index = 0
            exceptions = self._fetchTaskExceptions(int(row["id"]), str(row.get("timezone") or "UTC"))

            while occurrence_due <= range_end:
                occurrence_index += 1
                if count_limit is not None and occurrence_index > count_limit:
                    break
                if until is not None and occurrence_due > until:
                    break

                if occurrence_due >= range_start:
                    candidate = dict(row)
                    candidate["series_id"] = row.get("id")
                    candidate["occurrence_index"] = occurrence_index
                    candidate["due_at"] = occurrence_due.strftime("%Y-%m-%d %H:%M:%S")
                    exception = exceptions.get(candidate["due_at"])
                    if exception is not None:
                        if exception.get("exception_type") == "cancel":
                            occurrence_due = self._advanceOccurrence(
                                occurrence_due,
                                row.get("recurrence_type"),
                                int(row.get("recurrence_interval") or 1),
                            )
                            continue
                        candidate = self._applyTaskOccurrenceOverride(candidate, exception)
                    expanded.append(candidate)

                occurrence_due = self._advanceOccurrence(
                    occurrence_due,
                    row.get("recurrence_type"),
                    int(row.get("recurrence_interval") or 1),
                )

        return expanded

    def _expandRecurringReminders(self, rows, range_start_text: str, range_end_text: str):
        """Expand recurring reminders into concrete instances for a date range."""

        range_start = self._parseDateTime(range_start_text)
        range_end = self._parseDateTime(range_end_text)
        expanded = []

        for row in rows:
            if not row.get("recurrence_type"):
                expanded.append(row)
                continue

            base_remind = self._parseDateTime(row["remind_at"])
            until = self._parseDateTime(row["recurrence_until"]) if row.get("recurrence_until") else None
            count_limit = row.get("recurrence_count")
            occurrence_remind = base_remind
            occurrence_index = 0
            exceptions = self._fetchReminderExceptions(
                int(row["id"]),
                str(row.get("timezone") or "UTC"),
            )

            while occurrence_remind <= range_end:
                occurrence_index += 1
                if count_limit is not None and occurrence_index > count_limit:
                    break
                if until is not None and occurrence_remind > until:
                    break

                if occurrence_remind >= range_start:
                    candidate = dict(row)
                    candidate["series_id"] = row.get("id")
                    candidate["occurrence_index"] = occurrence_index
                    candidate["remind_at"] = occurrence_remind.strftime("%Y-%m-%d %H:%M:%S")
                    exception = exceptions.get(candidate["remind_at"])
                    if exception is not None:
                        if exception.get("exception_type") == "cancel":
                            occurrence_remind = self._advanceOccurrence(
                                occurrence_remind,
                                row.get("recurrence_type"),
                                int(row.get("recurrence_interval") or 1),
                            )
                            continue
                        candidate = self._applyReminderOccurrenceOverride(candidate, exception)
                    expanded.append(candidate)

                occurrence_remind = self._advanceOccurrence(
                    occurrence_remind,
                    row.get("recurrence_type"),
                    int(row.get("recurrence_interval") or 1),
                )

        return expanded

    def _applyOccurrenceOverride(self, candidate: dict, exception: dict) -> dict:
        """
        Apply one stored recurrence override to a generated event instance.
        """

        overridden = dict(candidate)

        field_map = {
            "override_title": "title",
            "override_description": "description",
            "override_location": "location",
            "override_start_at": "start_at",
            "override_end_at": "end_at",
            "override_all_day": "all_day",
            "override_status": "status",
        }

        for source_key, target_key in field_map.items():
            if exception.get(source_key) is not None:
                overridden[target_key] = exception[source_key]

        if exception.get("override_attendees") not in (None, []):
            overridden["attendees"] = list(exception["override_attendees"])

        overridden["has_exception"] = True
        overridden["exception_id"] = exception.get("id")
        return overridden

    def _applyTaskOccurrenceOverride(self, candidate: dict, exception: dict) -> dict:
        """Apply one stored task recurrence override to a generated task instance."""

        overridden = dict(candidate)

        field_map = {
            "override_title": "title",
            "override_description": "description",
            "override_due_at": "due_at",
            "override_priority": "priority",
            "override_status": "status",
        }
        for source_key, target_key in field_map.items():
            if exception.get(source_key) is not None:
                overridden[target_key] = exception[source_key]

        if exception.get("override_categories") is not None:
            overridden["categories"] = list(exception["override_categories"])
        if exception.get("override_notification_preferences") is not None:
            overridden["notification_preferences"] = exception["override_notification_preferences"]

        overridden["has_exception"] = True
        overridden["exception_id"] = exception.get("id")
        return overridden

    def _applyReminderOccurrenceOverride(self, candidate: dict, exception: dict) -> dict:
        """Apply one stored reminder recurrence override to a generated reminder instance."""

        overridden = dict(candidate)

        field_map = {
            "override_title": "title",
            "override_notes": "notes",
            "override_remind_at": "remind_at",
        }
        for source_key, target_key in field_map.items():
            if exception.get(source_key) is not None:
                overridden[target_key] = exception[source_key]

        if exception.get("override_notification_preferences") is not None:
            overridden["notification_preferences"] = exception["override_notification_preferences"]

        overridden["has_exception"] = True
        overridden["exception_id"] = exception.get("id")
        return overridden

    def _advanceOccurrence(self, current: datetime, recurrence_type: str, interval: int) -> datetime:
        """
        Advance one recurrence instance by its configured interval.
        """

        if recurrence_type == "daily":
            return current + timedelta(days=interval)
        if recurrence_type == "weekly":
            return current + timedelta(weeks=interval)
        if recurrence_type == "monthly":
            return self._addMonths(current, interval)
        if recurrence_type == "yearly":
            return self._addYears(current, interval)
        raise ValueError("Unsupported recurrence type.")

    def _eventOverlapsRange(self, row, range_start: datetime, range_end: datetime) -> bool:
        """
        Determine whether an event instance overlaps the provided range.
        """

        event_start = self._parseDateTime(row["start_at"])
        event_end = self._parseDateTime(row["end_at"]) if row.get("end_at") else event_start
        return event_start <= range_end and event_end >= range_start

    @staticmethod
    def _parseDateTime(value: str) -> datetime:
        """
        Parse a normalized MySQL datetime string into a datetime object.
        """

        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _addMonths(value: datetime, months: int) -> datetime:
        """
        Add months to a datetime while clamping day overflow to month length.
        """

        total_month = value.month - 1 + months
        year = value.year + total_month // 12
        month = total_month % 12 + 1
        day = min(value.day, month_calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    @staticmethod
    def _addYears(value: datetime, years: int) -> datetime:
        """
        Add years to a datetime while handling leap-day overflow safely.
        """

        year = value.year + years
        day = min(value.day, month_calendar.monthrange(year, value.month)[1])
        return value.replace(year=year, day=day)

    def _normalizeDateTimeValue(
        self,
        value: str,
        allow_date_only: bool = False,
        source_timezone: str = "UTC",
        target_timezone: str = "UTC",
    ) -> str:
        """
        Normalize a datetime between timezones into `YYYY-MM-DD HH:MM:SS`.
        """

        if value is None:
            raise ValueError("A datetime value is required.")

        raw_value = str(value).strip()
        if raw_value == "":
            raise ValueError("A datetime value is required.")

        accepted_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        ]

        if allow_date_only:
            accepted_formats.extend(["%Y-%m-%d", "%d/%m/%Y"])

        for format_string in accepted_formats:
            try:
                parsed = datetime.strptime(raw_value, format_string)
                if format_string in {"%Y-%m-%d", "%d/%m/%Y"}:
                    parsed = parsed.replace(hour=0, minute=0, second=0)
                converted = self._convertNaiveBetweenTimezones(
                    parsed,
                    source_timezone,
                    target_timezone,
                )
                return converted.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        raise ValueError(
            "Invalid date/time value. Use YYYY-MM-DD HH:MM or DD/MM/YYYY HH:MM."
        )

    def _convertStoredDateTimeToDisplay(self, value: Optional[str], target_timezone: str) -> Optional[str]:
        """Convert a UTC-stored datetime string into a calendar-local display string."""

        if value in (None, ""):
            return None
        parsed = self._parseDateTime(str(value))
        converted = self._convertNaiveBetweenTimezones(parsed, "UTC", target_timezone)
        return converted.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _coerceTimezone(timezone_name: Optional[str]):
        """Resolve a timezone name, defaulting invalid values to UTC."""

        try:
            return ZoneInfo(str(timezone_name or "UTC"))
        except Exception:
            return None

    def _convertNaiveBetweenTimezones(
        self,
        value: datetime,
        source_timezone: str,
        target_timezone: str,
    ) -> datetime:
        """Convert a naive datetime between two named timezones."""

        source_zone = self._coerceTimezone(source_timezone)
        target_zone = self._coerceTimezone(target_timezone)
        if source_zone is not None and target_zone is not None:
            source_value = value.replace(tzinfo=source_zone)
            converted = source_value.astimezone(target_zone)
            return converted.replace(tzinfo=None)

        utc_value = value - timedelta(minutes=self._resolveUtcOffsetMinutes(source_timezone, value))
        return utc_value + timedelta(
            minutes=self._resolveUtcOffsetMinutes(target_timezone, utc_value, is_utc_reference=True)
        )

    def _resolveUtcOffsetMinutes(
        self,
        timezone_name: Optional[str],
        reference: datetime,
        is_utc_reference: bool = False,
    ) -> int:
        """Return the UTC offset in minutes for supported timezones."""

        normalized = str(timezone_name or "UTC").strip()
        if normalized.upper() in {"UTC", "GMT", "Z"}:
            return 0

        fixed_offset = self._parseFixedOffsetMinutes(normalized)
        if fixed_offset is not None:
            return fixed_offset

        if normalized in {"America/Toronto", "America/New_York", "America/Montreal"}:
            return -240 if self._isNorthAmericaDst(reference, -300, is_utc_reference) else -300
        if normalized in {"America/Chicago", "America/Winnipeg"}:
            return -300 if self._isNorthAmericaDst(reference, -360, is_utc_reference) else -360
        if normalized in {"America/Denver", "America/Edmonton"}:
            return -360 if self._isNorthAmericaDst(reference, -420, is_utc_reference) else -420
        if normalized in {"America/Los_Angeles", "America/Vancouver"}:
            return -420 if self._isNorthAmericaDst(reference, -480, is_utc_reference) else -480
        if normalized == "Europe/London":
            return 60 if self._isEuropeLondonDst(reference, is_utc_reference) else 0

        return 0

    @staticmethod
    def _parseFixedOffsetMinutes(value: str) -> Optional[int]:
        """Parse a fixed offset string like `+02:00` or `-0500` into minutes."""

        if len(value) < 3 or value[0] not in {"+", "-"}:
            return None

        raw = value[1:].replace(":", "")
        if len(raw) not in {2, 4} or not raw.isdigit():
            return None

        hours = int(raw[:2])
        minutes = int(raw[2:4]) if len(raw) == 4 else 0
        total = hours * 60 + minutes
        return total if value[0] == "+" else -total

    def _isNorthAmericaDst(
        self,
        reference: datetime,
        standard_offset_minutes: int,
        is_utc_reference: bool,
    ) -> bool:
        """Return whether a reference falls inside North American DST rules."""

        year = reference.year
        dst_start_local = self._nthWeekdayOfMonth(year, 3, 6, 2).replace(hour=2, minute=0, second=0)
        dst_end_local = self._nthWeekdayOfMonth(year, 11, 6, 1).replace(hour=2, minute=0, second=0)

        if is_utc_reference:
            dst_start_utc = dst_start_local - timedelta(minutes=standard_offset_minutes)
            dst_end_utc = dst_end_local - timedelta(minutes=standard_offset_minutes + 60)
            return dst_start_utc <= reference < dst_end_utc

        return dst_start_local <= reference < dst_end_local

    def _isEuropeLondonDst(self, reference: datetime, is_utc_reference: bool) -> bool:
        """Return whether a reference falls inside London DST rules."""

        year = reference.year
        dst_start_utc = self._lastWeekdayOfMonth(year, 3, 6).replace(hour=1, minute=0, second=0)
        dst_end_utc = self._lastWeekdayOfMonth(year, 10, 6).replace(hour=1, minute=0, second=0)
        if is_utc_reference:
            return dst_start_utc <= reference < dst_end_utc

        dst_start_local = dst_start_utc
        dst_end_local = dst_end_utc + timedelta(hours=1)
        return dst_start_local <= reference < dst_end_local

    @staticmethod
    def _nthWeekdayOfMonth(year: int, month: int, weekday: int, occurrence: int) -> datetime:
        """Return the Nth weekday within a month."""

        first_weekday, days_in_month = month_calendar.monthrange(year, month)
        day = 1 + ((weekday - first_weekday) % 7) + ((occurrence - 1) * 7)
        day = min(day, days_in_month)
        return datetime(year, month, day)

    @staticmethod
    def _lastWeekdayOfMonth(year: int, month: int, weekday: int) -> datetime:
        """Return the last matching weekday within a month."""

        days_in_month = month_calendar.monthrange(year, month)[1]
        value = datetime(year, month, days_in_month)
        while value.weekday() != weekday:
            value -= timedelta(days=1)
        return value

    def _normalizeDateValue(self, value: str) -> str:
        """
        Normalize a date-only value to `YYYY-MM-DD`.
        """

        raw_value = str(value).strip()
        for format_string in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw_value, format_string).strftime("%Y-%m-%d")
            except ValueError:
                continue

        raise ValueError("Invalid date value. Use YYYY-MM-DD or DD/MM/YYYY.")

    @staticmethod
    def _parseDate(value: str) -> datetime:
        """
        Parse a normalized date string into a datetime at midnight.
        """

        return datetime.strptime(value, "%Y-%m-%d")

    def _updateRow(
        self,
        table_name: str,
        row_id: int,
        fields: Dict[str, object],
        allowed_fields: set[str],
        datetime_fields: set[str],
    ):
        """
        Apply a dynamic partial update to one calendar table row.
        """

        if not self.database:
            return

        update_parts = []
        params = []

        for key, value in fields.items():
            if key not in allowed_fields:
                continue

            normalized_value = value
            if key in datetime_fields and value is not None:
                normalized_value = self._normalizeDateTimeValue(str(value))

            update_parts.append(f"{key} = ?")
            params.append(normalized_value)

        if not update_parts:
            raise ValueError("No valid fields were provided for update.")

        params.append(int(row_id))
        self.database.execute(
            f"UPDATE {table_name} SET " + ", ".join(update_parts) + " WHERE id = ?",
            tuple(params),
        )
