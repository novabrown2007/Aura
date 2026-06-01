"""Weather alert coordination for Aura."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.weather.alerts import EmergencyAlertMonitor, WeatherThresholdMonitor
from modules.weather.models import WeatherAlert, WeatherData, WeatherThreshold
from modules.weather.weatherNotificationManager import WeatherNotificationManager


class WeatherAlertManager:
    """Coordinate weather alerts and threshold notifications."""

    def __init__(self, context=None, store=None, notificationManager=None):
        self.context = context
        self.store = store
        self.notificationManager = notificationManager or WeatherNotificationManager(context)
        self.thresholdMonitor = WeatherThresholdMonitor(context, self.notificationManager)
        self.emergencyMonitor = EmergencyAlertMonitor(context, self.notificationManager)
        self.logger = context.logger.getChild("Weather.Alerts") if context and getattr(context, "logger", None) else None
        self.lastTriggeredAlerts: list[dict[str, Any]] = []

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Alerts") if getattr(context, "logger", None) else None
            self.notificationManager.initialize(context)
            self.thresholdMonitor.initialize(context)
            self.emergencyMonitor.initialize(context)
        return self

    def loadThresholds(self, thresholds):
        self.thresholdMonitor.thresholds = {threshold.thresholdId or f"threshold-{index}": threshold for index, threshold in enumerate(list(thresholds or []), start=1)}

    def registerThreshold(self, threshold):
        if not isinstance(threshold, WeatherThreshold):
            threshold = WeatherThreshold.fromDict(threshold)
        self.thresholdMonitor.register(threshold)
        if self.store is not None:
            self.store.upsertThreshold(threshold.asDict())
        return threshold

    def removeThreshold(self, thresholdId: str):
        self.thresholdMonitor.remove(thresholdId)
        if self.store is not None:
            self.store.deleteThreshold(thresholdId)

    def listThresholds(self):
        return self.thresholdMonitor.listThresholds()

    def recordAlert(self, alert):
        if not isinstance(alert, WeatherAlert):
            alert = WeatherAlert.fromDict(alert)
        payload = alert.asDict()
        if self.store is not None:
            self.store.recordAlert(payload)
        self.lastTriggeredAlerts.append(payload)
        return payload

    def evaluateWeather(self, weatherData: WeatherData):
        triggeredThresholds = []
        if weatherData is None:
            return triggeredThresholds
        for threshold in self.thresholdMonitor.evaluate(weatherData):
            triggeredThresholds.append(threshold.asDict())
            self.notificationManager.notifyThreshold(threshold, weatherData)
            self._emit("weather.threshold.triggered", {"threshold": threshold.asDict(), "weather": weatherData.asDict()})
        return triggeredThresholds

    def evaluateAlerts(self, alerts):
        triggered = self.emergencyMonitor.evaluate(alerts)
        for alert in triggered:
            self.recordAlert(alert)
            self._emit("weather.alert.received", alert)
        return triggered

    def snapshot(self):
        return {
            "thresholds": self.thresholdMonitor.listThresholds(),
            "alerts": list(self.lastTriggeredAlerts),
        }

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload)
