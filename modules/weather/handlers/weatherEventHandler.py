"""Event bridge for the weather module."""

from __future__ import annotations


class WeatherEventHandler:
    """Translate runtime events into weather module refreshes."""

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager
        self.logger = context.logger.getChild("Weather.Events") if context and getattr(context, "logger", None) else None

    def subscribe(self):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return
        for eventName in ("bridge.sensor.updated", "schedule.tick", "system.started", "location.updated"):
            eventBus.subscribe(eventName, self.handleEvent)

    def unsubscribe(self):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return
        for eventName in ("bridge.sensor.updated", "schedule.tick", "system.started", "location.updated"):
            eventBus.unsubscribe(eventName, self.handleEvent)

    def handleEvent(self, event):
        eventName = getattr(event, "name", "")
        payload = dict(getattr(event, "data", {}) or {})
        if self.manager is None:
            return None
        if eventName == "bridge.sensor.updated":
            location = str(payload.get("location") or payload.get("room") or "")
            return self.manager.refreshCurrentWeather(location)
        if eventName == "schedule.tick":
            return self.manager.monitor.poll()
        if eventName == "system.started":
            return self.manager.monitor.poll(force=True)
        if eventName == "location.updated":
            location = str(payload.get("location") or payload.get("name") or "")
            return self.manager.refreshCurrentWeather(location)
        return None
