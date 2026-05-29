"""Notification category model."""

from __future__ import annotations

from enum import Enum


class NotificationCategory(str, Enum):
    """Supported notification categories."""

    SYSTEM = "SYSTEM"
    SMART_HOME = "SMART_HOME"
    SECURITY = "SECURITY"
    VOICE = "VOICE"
    REMINDER = "REMINDER"
    CALENDAR = "CALENDAR"
    EMAIL = "EMAIL"
    MEDIA = "MEDIA"
    AUTOMATION = "AUTOMATION"
    WARNING = "WARNING"
    EMERGENCY = "EMERGENCY"

    @classmethod
    def normalize(cls, value: "NotificationCategory | str | None") -> "NotificationCategory":
        if isinstance(value, cls):
            return value
        text = str(value or "SYSTEM").strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "HOME": cls.SMART_HOME,
            "SMARTHOME": cls.SMART_HOME,
            "SMARTHOME": cls.SMART_HOME,
            "NOTIFICATION": cls.SYSTEM,
            "ALERT": cls.WARNING,
        }
        if text in aliases:
            return aliases[text]
        try:
            return cls[text]
        except Exception:
            return cls.SYSTEM
