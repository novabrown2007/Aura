"""Notification delivery mode model."""

from __future__ import annotations

from enum import Enum


class NotificationDeliveryMode(str, Enum):
    """Supported notification delivery modes."""

    SILENT = "SILENT"
    UI_ONLY = "UI_ONLY"
    VOICE = "VOICE"
    VOICE_AND_UI = "VOICE_AND_UI"
    PERSISTENT = "PERSISTENT"
    INTERRUPT = "INTERRUPT"

    @classmethod
    def normalize(cls, value: "NotificationDeliveryMode | str | None") -> "NotificationDeliveryMode":
        if isinstance(value, cls):
            return value
        text = str(value or "UI_ONLY").strip().upper()
        try:
            return cls[text]
        except Exception:
            return cls.UI_ONLY
