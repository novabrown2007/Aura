"""Deterministic notification classification rules."""

from __future__ import annotations

from assistant.notifications.models.notificationCategory import NotificationCategory
from assistant.notifications.models.notificationPriority import NotificationPriority


class NotificationRules:
    """Keyword and event-based rules for notification classification."""

    HIGH_SECURITY_KEYWORDS = ("motion detected", "door opened", "unexpected", "unusual activity")
    CRITICAL_KEYWORDS = ("smoke detected", "fire", "water leak", "security breach")
    EMERGENCY_KEYWORDS = ("confirmed fire", "medical emergency", "panic", "ambulance", "cardiac arrest")
    LOW_KEYWORDS = ("disconnected", "stopped", "update", "weather")

    @classmethod
    def categoryFromEvent(cls, eventName: str, payload: dict | None = None) -> NotificationCategory:
        text = f"{eventName} {(payload or {}).get('title', '')} {(payload or {}).get('message', '')}".lower()
        if any(keyword in text for keyword in cls.EMERGENCY_KEYWORDS):
            return NotificationCategory.EMERGENCY
        if any(keyword in text for keyword in cls.CRITICAL_KEYWORDS):
            return NotificationCategory.SECURITY
        if any(keyword in text for keyword in cls.HIGH_SECURITY_KEYWORDS):
            return NotificationCategory.SECURITY
        if "timer" in text or "remind" in text:
            return NotificationCategory.REMINDER
        if "calendar" in text or "event" in text:
            return NotificationCategory.CALENDAR
        if "email" in text or "mail" in text:
            return NotificationCategory.EMAIL
        if "spotify" in text or "music" in text or "playback" in text:
            return NotificationCategory.MEDIA
        if "light" in text or "home" in text or "smart" in text:
            return NotificationCategory.SMART_HOME
        if "automation" in text:
            return NotificationCategory.AUTOMATION
        if any(keyword in text for keyword in cls.LOW_KEYWORDS):
            return NotificationCategory.WARNING
        return NotificationCategory.SYSTEM

    @classmethod
    def priorityFromEvent(cls, eventName: str, payload: dict | None = None) -> NotificationPriority:
        text = f"{eventName} {(payload or {}).get('title', '')} {(payload or {}).get('message', '')}".lower()
        if any(keyword in text for keyword in cls.EMERGENCY_KEYWORDS):
            return NotificationPriority.EMERGENCY
        if any(keyword in text for keyword in cls.CRITICAL_KEYWORDS):
            return NotificationPriority.CRITICAL
        if any(keyword in text for keyword in cls.HIGH_SECURITY_KEYWORDS):
            return NotificationPriority.HIGH
        if "timer.completed" in text or "email.received" in text or "calendar" in text:
            return NotificationPriority.NORMAL
        if any(keyword in text for keyword in cls.LOW_KEYWORDS):
            return NotificationPriority.LOW
        return NotificationPriority.NORMAL

    @staticmethod
    def inferSuppressionKey(payload: dict | None) -> str:
        payload = payload or {}
        parts = [
            str(payload.get("source") or payload.get("source_module") or ""),
            str(payload.get("category") or ""),
            str(payload.get("title") or ""),
            str(payload.get("message") or payload.get("content") or ""),
        ]
        return "|".join(part.strip().lower() for part in parts)
