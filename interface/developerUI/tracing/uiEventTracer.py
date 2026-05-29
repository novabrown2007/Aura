"""Event tracing for the Aura Developer UI."""

from __future__ import annotations

from time import perf_counter, time
from typing import Callable

from interface.developerUI.models import ConsoleEvent


class UIEventTracer:
    """Trace Aura event bus emissions and route them into developer UI state."""

    def __init__(self, context, state, performanceTracker=None, traceEvents: bool = True):
        self.context = context
        self.state = state
        self.performanceTracker = performanceTracker
        self.traceEvents = bool(traceEvents)
        self.originalEmit: Callable | None = None
        self.installed = False
        self.suppressedEvents = {"task_completed"}
        self.throttledEvents = {
            "memory.retrieval.completed": 10.0,
            "memory.injected": 10.0,
        }
        self._lastTraceAt: dict[str, float] = {}
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("DeveloperUI.EventTracer") if logger else None

    def install(self):
        """Wrap eventManager.emit so all event flow becomes visible."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or self.installed or not self.traceEvents:
            return
        self.originalEmit = eventManager.emit

        def tracedEmit(event, data=None):
            name = getattr(event, "name", event)
            payload = getattr(event, "data", data) if not isinstance(event, str) else data
            start = perf_counter()
            error = ""
            try:
                return self.originalEmit(event, data)
            except Exception as exc:
                error = str(exc)
                raise
            finally:
                durationMs = (perf_counter() - start) * 1000.0
                self.trace(str(name), payload or {}, durationMs=durationMs, error=error)

        eventManager.emit = tracedEmit
        self.installed = True
        if self.logger:
            self.logger.info("Developer UI event tracer installed.")

    def uninstall(self):
        """Restore the original event emitter."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is not None and self.installed and self.originalEmit is not None:
            eventManager.emit = self.originalEmit
        self.installed = False

    def trace(self, name: str, payload: dict | None = None, durationMs: float = 0.0, error: str = ""):
        """Record one event in UI state."""

        if not error and not self._shouldTrace(name):
            return
        event = ConsoleEvent(
            name=str(name),
            payload=payload if isinstance(payload, dict) else {"value": payload},
            category=self._category(str(name)),
            durationMs=durationMs,
            error=error,
        )
        self.state.recordEvent(event)
        if self.performanceTracker is not None:
            self.performanceTracker.record(event.name, durationMs, category="event")

    def _shouldTrace(self, name: str) -> bool:
        """Return whether an event is useful enough for the live console."""

        eventName = str(name or "")
        if eventName in self.suppressedEvents:
            return False
        interval = self.throttledEvents.get(eventName)
        if interval is None:
            return True
        now = time()
        last = self._lastTraceAt.get(eventName, 0.0)
        if now - last < interval:
            return False
        self._lastTraceAt[eventName] = now
        return True

    @staticmethod
    def _category(name: str) -> str:
        if "." in name:
            return name.split(".", 1)[0]
        return "general"
