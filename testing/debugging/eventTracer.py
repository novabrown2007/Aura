"""Internal event tracing for assistant ecosystem simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TracedEvent:
    """One traced assistant event."""

    category: str
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_utcNow)


class EventTracer:
    """Record assistant simulation events for later inspection."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Testing.Tracer") if context and getattr(context, "logger", None) else None
        self.events: list[TracedEvent] = []

    def trace(self, category: str, name: str, data: dict[str, Any] | None = None):
        """Record a single traced event."""

        event = TracedEvent(category=str(category or ""), name=str(name or ""), data=dict(data or {}))
        self.events.append(event)
        if self.logger:
            self.logger.debug(f"[{event.category}] {event.name}")
        return event

    def traceIntent(self, intent: dict[str, Any]):
        """Trace a structured intent event."""

        return self.trace("intent", str(intent.get("intent") or intent.get("name") or ""), intent)

    def traceResponse(self, response: str, data: dict[str, Any] | None = None):
        """Trace an assistant response event."""

        payload = dict(data or {})
        payload["response"] = response
        return self.trace("response", "assistant.response", payload)

    def traceNotification(self, notification: dict[str, Any]):
        """Trace a notification event."""

        return self.trace("notification", str(notification.get("event") or notification.get("category") or ""), notification)

    def traceSession(self, sessionId: str, state: dict[str, Any] | None = None):
        """Trace a session lifecycle event."""

        payload = dict(state or {})
        payload["sessionId"] = sessionId
        return self.trace("session", "session.lifecycle", payload)

    def traceProtocol(self, name: str, data: dict[str, Any] | None = None):
        """Trace a protocol routing event."""

        return self.trace("protocol", name, data)

    def getEvents(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return traced events as plain dictionaries."""

        events = self.events[-limit:] if limit else self.events
        return [
            {"category": item.category, "name": item.name, "data": dict(item.data), "timestamp": item.timestamp}
            for item in events
        ]

    def clear(self):
        """Clear traced events."""

        self.events.clear()

    def getLastEvent(self) -> dict[str, Any] | None:
        """Return the most recently traced event as a dictionary."""

        if not self.events:
            return None
        event = self.events[-1]
        return {
            "category": event.category,
            "name": event.name,
            "data": dict(event.data),
            "timestamp": event.timestamp,
        }

    def snapshot(self) -> dict[str, Any]:
        """Return the tracer state in a serializable form."""

        return {"events": self.getEvents()}
