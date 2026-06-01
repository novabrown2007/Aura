"""Emergency weather alert monitoring for Aura."""

from __future__ import annotations


class EmergencyAlertMonitor:
    """Escalate severe weather alerts to notifications and overlays."""

    EMERGENCY_KEYWORDS = ("tornado", "flood", "hurricane", "blizzard", "storm warning", "severe thunderstorm", "heat warning", "cold warning")

    def __init__(self, context=None, notificationManager=None):
        self.context = context
        self.notificationManager = notificationManager
        self.logger = context.logger.getChild("Weather.Emergency") if context and getattr(context, "logger", None) else None

    def initialize(self, context=None):
        if context is not None:
            self.context = context
            self.logger = context.logger.getChild("Weather.Emergency") if getattr(context, "logger", None) else None
        return self

    def evaluate(self, alerts):
        triggered = []
        for alert in list(alerts or []):
            payload = alert.asDict() if hasattr(alert, "asDict") else dict(alert or {})
            severity = str(payload.get("severity") or "LOW").upper()
            text = f"{payload.get('title', '')} {payload.get('message', '')}".lower()
            if severity in {"HIGH", "CRITICAL"} or any(keyword in text for keyword in self.EMERGENCY_KEYWORDS):
                triggered.append(payload)
                if self.notificationManager is not None:
                    self.notificationManager.notifyAlert(payload, eventName="weather.alert.received")
        return triggered
