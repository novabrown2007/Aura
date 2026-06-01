"""Weather notification routing for Aura."""

from __future__ import annotations

from typing import Any

from assistant.notifications.models.notificationCategory import NotificationCategory
from assistant.notifications.models.notificationPriority import NotificationPriority


class WeatherNotificationManager:
    """Route weather notifications through Aura's assistant notification system."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Weather.Notifications") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Notifications") if getattr(context, "logger", None) else None
        return self

    def notifyWeather(self, title: str, message: str, priority: str = "NORMAL", category: str = "WARNING", metadata: dict[str, Any] | None = None, eventName: str = "weather.updated"):
        """Create one weather notification if the notification manager is available."""

        notificationManager = getattr(self.context, "notificationManager", None)
        payload = {
            "title": str(title or ""),
            "message": str(message or ""),
            "priority": NotificationPriority.normalize(priority).value,
            "category": NotificationCategory.normalize(category).value,
            "source": "weather",
            "metadata": dict(metadata or {}),
        }
        if notificationManager is None:
            return payload
        try:
            return notificationManager.createNotification(payload, eventName=eventName)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Weather notification failed: {error}")
            return payload

    def notifyAlert(self, alert, eventName: str = "weather.alert.received"):
        payload = alert.asDict() if hasattr(alert, "asDict") else dict(alert or {})
        priority = payload.get("severity") or "NORMAL"
        category = "EMERGENCY" if str(priority).upper() in {"HIGH", "CRITICAL"} else "WARNING"
        return self.notifyWeather(
            title=str(payload.get("title") or "Weather alert"),
            message=str(payload.get("message") or ""),
            priority="CRITICAL" if str(priority).upper() == "CRITICAL" else "HIGH" if str(priority).upper() == "HIGH" else "NORMAL",
            category=category,
            metadata=payload,
            eventName=eventName,
        )

    def notifyThreshold(self, threshold, weatherData, eventName: str = "weather.threshold.triggered"):
        thresholdPayload = threshold.asDict() if hasattr(threshold, "asDict") else dict(threshold or {})
        weatherPayload = weatherData.asDict() if hasattr(weatherData, "asDict") else dict(weatherData or {})
        return self.notifyWeather(
            title=str(thresholdPayload.get("title") or "Weather threshold reached"),
            message=str(thresholdPayload.get("message") or f"{thresholdPayload.get('metric', 'Weather')} threshold reached."),
            priority=str(thresholdPayload.get("notificationPriority") or "NORMAL"),
            category="WARNING",
            metadata={"threshold": thresholdPayload, "weather": weatherPayload},
            eventName=eventName,
        )
