"""Standard-library web interface for Aura."""

from __future__ import annotations

import json
import mimetypes
from datetime import date, datetime, timedelta
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


WEB_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = WEB_ROOT / "static"


class AuraWebApp:
    """HTTP web shell that calls Aura backend services directly."""

    def __init__(self, context, host: str = "127.0.0.1", port: int = 8765):
        self.context = context
        self.host = host
        self.port = int(port)
        self.selectedCalendarId = None
        self.logger = context.logger.getChild("WebApp") if context.logger else None
        self._server = None

    def serve_forever(self):
        """Run the web interface until the server is stopped."""

        self._server = createWebServer(self.context, self.host, self.port, app=self)
        if self.logger:
            self.logger.info("Web interface listening on http://%s:%s", self.host, self.port)
        try:
            self._server.serve_forever()
        finally:
            self.context.should_exit = True
            self._server.server_close()

    def shutdown(self):
        """Stop the web server if it is running."""

        if self._server is not None:
            self._server.shutdown()


def createWebServer(context, host: str = "127.0.0.1", port: int = 8765, app: AuraWebApp | None = None):
    """Create a configured ThreadingHTTPServer for the Aura web interface."""

    app = app or AuraWebApp(context, host=host, port=port)

    class Handler(AuraWebRequestHandler):
        aura_app = app
        aura_context = context

    return ThreadingHTTPServer((host, int(port)), Handler)


class AuraWebRequestHandler(SimpleHTTPRequestHandler):
    """Request handler for static assets and Aura JSON API routes."""

    aura_app: AuraWebApp
    aura_context = None
    server_version = "AuraWeb/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handleApi("GET", parsed.path, self._query(parsed))
            return
        self._serveStatic(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handleApi("POST", parsed.path, self._query(parsed), self._readJsonBody())
            return
        self._sendError(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handleApi("PUT", parsed.path, self._query(parsed), self._readJsonBody())
            return
        self._sendError(HTTPStatus.NOT_FOUND, "Route not found.")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._handleApi("DELETE", parsed.path, self._query(parsed), self._readJsonBody())
            return
        self._sendError(HTTPStatus.NOT_FOUND, "Route not found.")

    def log_message(self, format, *args):  # noqa: A002 - matches base API
        logger = getattr(self.aura_context, "logger", None)
        if logger:
            logger.getChild("WebHTTP").info(format, *args)

    def _handleApi(self, method: str, path: str, query: dict, body: dict | None = None):
        try:
            result = self._dispatchApi(method, path, query, body or {})
        except Exception as error:
            self._sendJson({"ok": False, "error": str(error)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._sendJson({"ok": True, "data": self._jsonSafe(result)})

    def _dispatchApi(self, method: str, path: str, query: dict, body: dict):
        context = self.aura_context

        if method == "GET" and path == "/api/health":
            return {"status": "online"}

        if method == "POST" and path == "/api/chat":
            message = str(body.get("message", "")).strip()
            if not message:
                raise ValueError("Message is required.")
            interpreter = context.require("interpreter")
            router = context.require("intentRouter")
            intent = interpreter.interpret(message)
            return {"response": str(router.route(intent))}

        if method == "GET" and path == "/api/reminders":
            return context.require("reminders").listReminders()

        if method == "POST" and path == "/api/reminders":
            return {
                "id": context.require("reminders").createReminder(
                    title=self._required(body, "title"),
                    content=str(body.get("content", "")),
                    module_of_origin="web",
                    reminder_at=self._blankToNone(body.get("reminder_at")),
                )
            }

        if method == "DELETE" and path.startswith("/api/reminders/"):
            reminder_id = self._pathId(path, "/api/reminders/")
            context.require("reminders").deleteReminder(reminder_id)
            return {"id": reminder_id}

        if method == "GET" and path == "/api/notifications":
            status = self._single(query, "status")
            limit = self._optionalInt(self._single(query, "limit"))
            return context.require("notifications").listNotifications(status=status, limit=limit)

        if method == "DELETE" and path.startswith("/api/notifications/"):
            notification_id = self._pathId(path, "/api/notifications/")
            context.require("notifications").deleteNotification(notification_id)
            return {"id": notification_id}

        if path.startswith("/api/calendar/"):
            return self._dispatchCalendarApi(method, path, query, body)

        raise ValueError("Unsupported API route.")

    def _dispatchCalendarApi(self, method: str, path: str, query: dict, body: dict):
        calendar = self.aura_context.require("calendar")

        if method == "GET" and path == "/api/calendar/calendars":
            return {
                "selected_calendar_id": self.aura_app.selectedCalendarId,
                "calendars": calendar.listCalendars(),
            }

        if method == "POST" and path == "/api/calendar/calendars":
            calendar.createCalendar(
                name=self._required(body, "name"),
                description=self._blankToNone(body.get("description")),
                color=self._blankToNone(body.get("color")),
                timezone=str(body.get("timezone") or "UTC"),
                visibility=str(body.get("visibility") or "private"),
                is_default=bool(body.get("is_default")),
            )
            return calendar.listCalendars()

        if method == "POST" and path == "/api/calendar/select":
            self.aura_app.selectedCalendarId = self._optionalInt(body.get("calendar_id"))
            return {"selected_calendar_id": self.aura_app.selectedCalendarId}

        if method == "GET" and path == "/api/calendar/view":
            view = self._single(query, "view") or "day"
            day_value = self._single(query, "date") or date.today().strftime("%Y-%m-%d")
            calendar_id = self._optionalInt(self._single(query, "calendar_id"))
            if calendar_id is None:
                calendar_id = self.aura_app.selectedCalendarId
            return self._buildCalendarView(calendar, view, day_value, calendar_id)

        if method == "POST" and path == "/api/calendar/events":
            return {"id": calendar.createEvent(**self._eventFields(body))}

        if method == "PUT" and path.startswith("/api/calendar/events/"):
            event_id = self._pathId(path, "/api/calendar/events/")
            calendar.updateEvent(event_id, **self._cleanFields(body))
            return calendar.getEvent(event_id)

        if method == "DELETE" and path.startswith("/api/calendar/events/"):
            event_id = self._pathId(path, "/api/calendar/events/")
            calendar.deleteEvent(event_id)
            return {"id": event_id}

        if method == "POST" and path == "/api/calendar/tasks":
            return {"id": calendar.createTask(**self._taskFields(body))}

        if method == "PUT" and path.startswith("/api/calendar/tasks/"):
            task_id = self._pathId(path, "/api/calendar/tasks/")
            calendar.updateTask(task_id, **self._cleanFields(body))
            return calendar.getTask(task_id)

        if method == "DELETE" and path.startswith("/api/calendar/tasks/"):
            task_id = self._pathId(path, "/api/calendar/tasks/")
            calendar.deleteTask(task_id)
            return {"id": task_id}

        if method == "POST" and path == "/api/calendar/reminders":
            return {"id": calendar.createReminder(**self._calendarReminderFields(body))}

        if method == "PUT" and path.startswith("/api/calendar/reminders/"):
            reminder_id = self._pathId(path, "/api/calendar/reminders/")
            calendar.updateReminder(reminder_id, **self._calendarReminderUpdateFields(body))
            return calendar.getReminder(reminder_id)

        if method == "DELETE" and path.startswith("/api/calendar/reminders/"):
            reminder_id = self._pathId(path, "/api/calendar/reminders/")
            calendar.deleteReminder(reminder_id)
            return {"id": reminder_id}

        if method == "POST" and path == "/api/calendar/search":
            query_text = self._blankToNone(body.get("query"))
            calendar_id = self._optionalInt(body.get("calendar_id"))
            return {
                "events": calendar.searchEvents(query=query_text, calendar_id=calendar_id),
                "tasks": calendar.searchTasks(query=query_text, calendar_id=calendar_id),
                "reminders": calendar.searchReminders(query=query_text, calendar_id=calendar_id),
            }

        if method == "POST" and path == "/api/calendar/conflicts":
            return calendar.detectConflicts(
                start_at=self._required(body, "start_at"),
                end_at=self._required(body, "end_at"),
                calendar_id=self._optionalInt(body.get("calendar_id")),
                exclude_event_id=self._optionalInt(body.get("exclude_event_id")),
            )

        if method == "POST" and path == "/api/calendar/occurrences/update":
            return self._updateOccurrence(calendar, body)

        if method == "POST" and path == "/api/calendar/occurrences/cancel":
            return self._cancelOccurrence(calendar, body)

        if method == "POST" and path == "/api/calendar/series/update":
            return self._updateSeries(calendar, body)

        if method == "POST" and path == "/api/calendar/series/delete":
            return self._deleteSeries(calendar, body)

        raise ValueError("Unsupported calendar API route.")

    def _buildCalendarView(self, calendar, view: str, day_value: str, calendar_id: int | None):
        if view == "week":
            return calendar.buildWeekView(day_value, calendar_id=calendar_id)
        if view == "month":
            return calendar.buildMonthView(day_value, calendar_id=calendar_id)
        if view == "year":
            start = datetime.strptime(calendar._normalizeDateValue(day_value), "%Y-%m-%d").date().replace(month=1, day=1)
            return {
                "year": start.year,
                "months": [
                    calendar.buildMonthView((start.replace(month=month)).strftime("%Y-%m-%d"), calendar_id=calendar_id)
                    for month in range(1, 13)
                ],
            }
        return calendar.buildDayView(day_value, calendar_id=calendar_id)

    def _eventFields(self, body: dict):
        fields = self._cleanFields(body)
        fields["title"] = self._required(body, "title")
        fields["start_at"] = self._required(body, "start_at")
        fields["calendar_id"] = self._optionalInt(body.get("calendar_id"))
        fields["linked_task_id"] = self._optionalInt(body.get("linked_task_id"))
        fields["recurrence_interval"] = int(body.get("recurrence_interval") or 1)
        fields["all_day"] = bool(body.get("all_day"))
        return fields

    def _taskFields(self, body: dict):
        fields = self._cleanFields(body)
        fields["title"] = self._required(body, "title")
        fields["calendar_id"] = self._optionalInt(body.get("calendar_id"))
        fields["linked_event_id"] = self._optionalInt(body.get("linked_event_id"))
        fields["recurrence_interval"] = int(body.get("recurrence_interval") or 1)
        return fields

    def _calendarReminderFields(self, body: dict):
        fields = self._cleanFields(body)
        fields["title"] = self._required(body, "title")
        fields["remind_at"] = self._required(body, "remind_at")
        fields["calendar_id"] = self._optionalInt(body.get("calendar_id"))
        fields["event_id"] = self._optionalInt(body.get("event_id") or body.get("linked_event_id"))
        fields["task_id"] = self._optionalInt(body.get("task_id") or body.get("linked_task_id"))
        if "content" in fields and "notes" not in fields:
            fields["notes"] = fields.pop("content")
        fields["recurrence_interval"] = int(body.get("recurrence_interval") or 1)
        return fields

    def _calendarReminderUpdateFields(self, body: dict):
        fields = self._cleanFields(body)
        if "content" in fields and "notes" not in fields:
            fields["notes"] = fields.pop("content")
        if "linked_event_id" in body and "event_id" not in fields:
            fields["event_id"] = self._optionalInt(body.get("linked_event_id"))
        if "linked_task_id" in body and "task_id" not in fields:
            fields["task_id"] = self._optionalInt(body.get("linked_task_id"))
        return fields

    def _updateOccurrence(self, calendar, body: dict):
        kind = self._required(body, "kind")
        item_id = int(self._required(body, "id"))
        fields = self._cleanFields(body.get("fields") or {})
        if kind == "task":
            calendar.updateTaskOccurrence(item_id, self._required(body, "occurrence_at"), **fields)
            return calendar.getTask(item_id)
        if kind == "reminder":
            calendar.updateReminderOccurrence(item_id, self._required(body, "occurrence_at"), **fields)
            return calendar.getReminder(item_id)
        calendar.updateOccurrence(item_id, self._required(body, "occurrence_at"), **fields)
        return calendar.getEvent(item_id)

    def _cancelOccurrence(self, calendar, body: dict):
        kind = self._required(body, "kind")
        item_id = int(self._required(body, "id"))
        occurrence_at = self._required(body, "occurrence_at")
        if kind == "task":
            calendar.cancelTaskOccurrence(item_id, occurrence_at)
        elif kind == "reminder":
            calendar.cancelReminderOccurrence(item_id, occurrence_at)
        else:
            calendar.cancelOccurrence(item_id, occurrence_at)
        return {"id": item_id}

    def _updateSeries(self, calendar, body: dict):
        kind = self._required(body, "kind")
        item_id = int(self._required(body, "id"))
        scope = str(body.get("scope") or "all")
        occurrence_at = self._blankToNone(body.get("occurrence_at"))
        fields = self._cleanFields(body.get("fields") or {})
        if kind == "task":
            calendar.updateTaskSeries(item_id, scope=scope, occurrence_due_at=occurrence_at, **fields)
            return calendar.getTask(item_id)
        if kind == "reminder":
            calendar.updateReminderSeries(item_id, scope=scope, occurrence_remind_at=occurrence_at, **fields)
            return calendar.getReminder(item_id)
        calendar.updateEventSeries(item_id, scope=scope, occurrence_start=occurrence_at, **fields)
        return calendar.getEvent(item_id)

    def _deleteSeries(self, calendar, body: dict):
        kind = self._required(body, "kind")
        item_id = int(self._required(body, "id"))
        scope = str(body.get("scope") or "all")
        occurrence_at = self._blankToNone(body.get("occurrence_at"))
        if kind == "task":
            calendar.deleteTaskSeries(item_id, scope=scope, occurrence_due_at=occurrence_at)
        elif kind == "reminder":
            calendar.deleteReminderSeries(item_id, scope=scope, occurrence_remind_at=occurrence_at)
        else:
            calendar.deleteEventSeries(item_id, scope=scope, occurrence_start=occurrence_at)
        return {"id": item_id}

    def _serveStatic(self, path: str):
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        if relative.startswith("assets/"):
            file_path = STATIC_ROOT / relative.removeprefix("assets/")
        else:
            file_path = STATIC_ROOT / relative

        resolved = file_path.resolve()
        if not str(resolved).startswith(str(STATIC_ROOT.resolve())) or not resolved.is_file():
            self._sendError(HTTPStatus.NOT_FOUND, "File not found.")
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _readJsonBody(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _sendJson(self, payload: dict, status=HTTPStatus.OK):
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _sendError(self, status, message: str):
        self._sendJson({"ok": False, "error": message}, status=status)

    @staticmethod
    def _query(parsed):
        return parse_qs(parsed.query, keep_blank_values=True)

    @staticmethod
    def _single(query: dict, key: str):
        values = query.get(key)
        if not values:
            return None
        return values[0] or None

    @staticmethod
    def _required(body: dict, key: str):
        value = body.get(key)
        if value is None or str(value).strip() == "":
            raise ValueError(f"{key} is required.")
        return value

    @staticmethod
    def _blankToNone(value):
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @classmethod
    def _optionalInt(cls, value):
        value = cls._blankToNone(value)
        return None if value is None else int(value)

    @staticmethod
    def _pathId(path: str, prefix: str) -> int:
        tail = path.removeprefix(prefix).strip("/")
        if "/" in tail or not tail:
            raise ValueError("Invalid route ID.")
        return int(tail)

    @classmethod
    def _cleanFields(cls, body: dict):
        ignored = {"id", "kind", "fields", "occurrence_at", "scope", "linked_event_id", "linked_task_id"}
        return {
            key: cls._blankToNone(value)
            for key, value in body.items()
            if key not in ignored and cls._blankToNone(value) is not None
        }

    @classmethod
    def _jsonSafe(cls, value):
        if isinstance(value, dict):
            return {str(key): cls._jsonSafe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._jsonSafe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value
