"""Weather monitoring loop for Aura."""

from __future__ import annotations

from datetime import datetime, timedelta


class WeatherMonitor:
    """Poll weather sources and evaluate thresholds on runtime ticks."""

    def __init__(self, context=None, manager=None):
        self.context = context
        self.manager = manager
        self.logger = context.logger.getChild("Weather.Monitor") if context and getattr(context, "logger", None) else None
        self.lastRefresh = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Monitor") if getattr(context, "logger", None) else None
        return self

    def poll(self, location: str = "", force: bool = False):
        """Refresh weather, alerts, and threshold rules when enough time has elapsed."""

        if self.manager is None:
            return None
        locations = [location] if location else self.manager.listLocationNames()
        if not locations:
            locations = [self.manager.resolveLocation("")]
        updated = []
        for item in locations:
            if not force and not self._shouldRefresh(item):
                continue
            current = self.manager.refreshCurrentWeather(item)
            self.manager.refreshAlerts(item)
            self.manager.refreshForecast(item)
            self.manager.evaluateThresholds(current)
            updated.append(current)
            self.lastRefresh[item] = self._now()
        return updated

    def snapshot(self):
        return {
            "lastRefresh": {key: value.strftime("%Y-%m-%d %H:%M:%S") for key, value in self.lastRefresh.items()},
            "intervalMinutes": self._intervalMinutes(),
        }

    def _shouldRefresh(self, location: str) -> bool:
        last = self.lastRefresh.get(location)
        if last is None:
            return True
        return self._now() - last >= timedelta(minutes=max(1, self._intervalMinutes()))

    def _intervalMinutes(self) -> int:
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return 15
        return int(config.get("weather.weatherRefreshIntervalMinutes", 15) or 15)

    @staticmethod
    def _now():
        return datetime.utcnow()
