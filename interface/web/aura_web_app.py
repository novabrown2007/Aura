"""Standard-library web interface for Aura."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from interface.model_status import format_current_model_label


WEB_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = WEB_ROOT / "static"


class AuraWebApp:
    """HTTP web shell that calls Aura backend services directly."""

    def __init__(self, context, host: str = "127.0.0.1", port: int = 8765):
        self.context = context
        self.host = host
        self.port = int(port)
        self.selectedScheduleId = None
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

        if method == "GET" and path == "/api/system/model":
            return {"current_model": format_current_model_label(context)}

        if method == "POST" and path == "/api/chat":
            message = str(body.get("message", "")).strip()
            if not message:
                raise ValueError("Message is required.")
            interpreter = context.require("interpreter")
            router = context.require("intentRouter")
            intent = interpreter.interpret(message)
            return {"response": str(router.route(intent))}

        if path.startswith("/api/schedule/"):
            return self._dispatchScheduleApi(method, path, query, body)

        if method == "GET" and path == "/api/notifications":
            status = self._single(query, "status")
            limit = self._optionalInt(self._single(query, "limit"))
            return context.require("notifications").listNotifications(status=status, limit=limit)

        if method == "DELETE" and path.startswith("/api/notifications/"):
            notification_id = self._pathId(path, "/api/notifications/")
            context.require("notifications").deleteNotification(notification_id)
            return {"id": notification_id}

        if path.startswith("/api/home-automation/"):
            return self._dispatchHomeAutomationApi(method, path, query, body)

        raise ValueError("Unsupported API route.")

    def _dispatchHomeAutomationApi(self, method: str, path: str, query: dict, body: dict):
        automation = self.aura_context.require("homeAutomation")

        if method == "GET" and path == "/api/home-automation/state":
            return automation.getBridgeState()

        if method == "POST" and path == "/api/home-automation/refresh":
            return automation.refresh()

        if method == "POST" and path == "/api/home-automation/bridge/start":
            return automation.startBridge()

        if method == "POST" and path == "/api/home-automation/hub/start":
            return automation.startHub()

        if method == "GET" and path == "/api/home-automation/notifications":
            return automation.getNotifications()

        if method == "POST" and path == "/api/home-automation/notifications":
            return automation.queueNotification(
                source=str(body.get("source") or "web"),
                severity=str(body.get("severity") or "info"),
                category=str(body.get("category") or "system"),
                title=self._required(body, "title"),
                message=self._required(body, "message"),
                device_id=str(body.get("device_id") or ""),
            )

        if method == "POST" and path.startswith("/api/home-automation/lights/"):
            parts = self._routeParts(path, "/api/home-automation/lights/")
            if len(parts) != 2:
                raise ValueError("Invalid light route.")
            device_id, action = parts
            if action == "state":
                return automation.toggleLight(
                    device_id,
                    bool(body.get("is_on")),
                    self._optionalInt(body.get("brightness")),
                )
            if action == "brightness":
                return automation.setLightBrightness(device_id, int(self._required(body, "brightness")))
            if action == "temperature":
                return automation.setLightTemperature(device_id, int(self._required(body, "kelvin")))
            if action == "color":
                return automation.setLightColor(device_id, self._required(body, "color"))
            raise ValueError("Unsupported light action.")

        if method == "POST" and path.startswith("/api/home-automation/cameras/"):
            parts = self._routeParts(path, "/api/home-automation/cameras/")
            if len(parts) != 2:
                raise ValueError("Invalid camera route.")
            device_id, action = parts
            if action == "start":
                return automation.startCameraStream(device_id)
            if action == "stop":
                return automation.stopCameraStream(device_id)
            if action == "snapshot":
                return automation.takeCameraSnapshot(device_id)
            raise ValueError("Unsupported camera action.")

        raise ValueError("Unsupported home automation API route.")

    def _dispatchScheduleApi(self, method: str, path: str, query: dict, body: dict):
        schedule = self.aura_context.require("personalSchedule")

        if method == "GET" and path == "/api/schedule/items":
            itemType = self._blankToNone(self._single(query, "type"))
            state = self._blankToNone(self._single(query, "state"))
            return [self._schedulePayload(item) for item in schedule.listScheduleItems(itemType=itemType, state=state)]

        if method == "GET" and path == "/api/schedule/today":
            return schedule.getTodaysSchedule()

        if method == "GET" and path == "/api/schedule/upcoming":
            limit = self._optionalInt(self._single(query, "limit")) or 10
            return schedule.getUpcomingSchedule(limit=limit)

        if method == "GET" and path == "/api/schedule/view":
            view = self._single(query, "view") or "day"
            day_value = self._single(query, "date") or date.today().strftime("%Y-%m-%d")
            if view == "week":
                return schedule.buildWeekView(day_value)
            if view == "month":
                return schedule.buildMonthView(day_value)
            return schedule.buildDayView(day_value)

        if method == "POST" and path == "/api/schedule/items":
            item = schedule.createScheduleItem(**self._cleanFields(body))
            return {"id": getattr(item, "itemId", None), "item": self._schedulePayload(item)}

        if method == "PUT" and path.startswith("/api/schedule/items/"):
            item_id = self._pathIdString(path, "/api/schedule/items/")
            item = schedule.updateScheduleItem(item_id, **self._cleanFields(body))
            return self._schedulePayload(item)

        if method == "DELETE" and path.startswith("/api/schedule/items/"):
            item_id = self._pathIdString(path, "/api/schedule/items/")
            schedule.deleteScheduleItem(item_id)
            return {"id": item_id}

        if method == "POST" and path == "/api/schedule/search":
            query_text = self._blankToNone(body.get("query"))
            return schedule.searchSchedule(query_text or "", limit=self._optionalInt(body.get("limit")) or 20)

        if method == "POST" and path == "/api/schedule/reminders":
            item = schedule.createReminder(**self._cleanFields(body))
            return {"id": getattr(item, "itemId", None), "item": self._schedulePayload(item)}

        if method == "POST" and path == "/api/schedule/tasks":
            item = schedule.createTask(**self._cleanFields(body))
            return {"id": getattr(item, "itemId", None), "item": self._schedulePayload(item)}

        if method == "POST" and path == "/api/schedule/timers":
            item = schedule.createTimer(**self._cleanFields(body))
            return {"id": getattr(item, "itemId", None), "item": self._schedulePayload(item)}

        if method == "POST" and path == "/api/schedule/timers/complete":
            item_id = self._required(body, "itemId")
            item = schedule.completeTimer(item_id)
            return {"id": getattr(item, "itemId", None), "item": self._schedulePayload(item)}

        raise ValueError("Unsupported schedule API route.")

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

    @staticmethod
    def _pathIdString(path: str, prefix: str) -> str:
        tail = path.removeprefix(prefix).strip("/")
        if "/" in tail or not tail:
            raise ValueError("Invalid route ID.")
        return tail

    @staticmethod
    def _routeParts(path: str, prefix: str) -> list[str]:
        tail = path.removeprefix(prefix).strip("/")
        return [part for part in tail.split("/") if part]

    @classmethod
    def _cleanFields(cls, body: dict):
        ignored = {"id", "itemId", "item_id", "kind", "fields", "occurrence_at", "scope"}
        return {
            key: cls._blankToNone(value)
            for key, value in body.items()
            if key not in ignored and cls._blankToNone(value) is not None
        }

    @classmethod
    def _jsonSafe(cls, value):
        if is_dataclass(value):
            return cls._jsonSafe(asdict(value))
        if isinstance(value, dict):
            return {str(key): cls._jsonSafe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._jsonSafe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    @classmethod
    def _schedulePayload(cls, item):
        if item is None:
            return None
        as_dict = getattr(item, "asDict", None)
        if callable(as_dict):
            return cls._jsonSafe(as_dict())
        if is_dataclass(item):
            return cls._jsonSafe(asdict(item))
        if hasattr(item, "__dict__"):
            return cls._jsonSafe(dict(vars(item)))
        return cls._jsonSafe(item)
