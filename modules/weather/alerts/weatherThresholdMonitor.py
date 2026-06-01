"""Weather threshold evaluation for Aura."""

from __future__ import annotations

from datetime import datetime


class WeatherThresholdMonitor:
    """Evaluate configured thresholds against current weather data."""

    def __init__(self, context=None, notificationManager=None):
        self.context = context
        self.notificationManager = notificationManager
        self.thresholds: dict[str, object] = {}
        self.logger = context.logger.getChild("Weather.Thresholds") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Thresholds") if getattr(context, "logger", None) else None
        return self

    def register(self, threshold):
        thresholdId = str(getattr(threshold, "thresholdId", "") or getattr(threshold, "id", "") or len(self.thresholds) + 1)
        self.thresholds[thresholdId] = threshold
        return threshold

    def remove(self, thresholdId: str):
        self.thresholds.pop(str(thresholdId), None)

    def listThresholds(self):
        return [threshold.asDict() if hasattr(threshold, "asDict") else dict(threshold or {}) for threshold in self.thresholds.values()]

    def evaluate(self, weatherData):
        triggered = []
        if weatherData is None:
            return triggered
        timestamp = self._now()
        for threshold in self.thresholds.values():
            if not getattr(threshold, "enabled", True):
                continue
            if getattr(threshold, "isCoolingDown", None) and threshold.isCoolingDown(timestamp):
                continue
            if threshold.evaluate(weatherData):
                threshold.markTriggered(timestamp)
                triggered.append(threshold)
        return triggered

    def snapshot(self):
        return {"thresholds": self.listThresholds(), "count": len(self.thresholds)}

    @staticmethod
    def _now():
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
