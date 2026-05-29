"""Notification priority model."""

from __future__ import annotations

from enum import Enum


class NotificationPriority(str, Enum):
    """Supported notification priority levels."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

    @classmethod
    def rank(cls, value: "NotificationPriority | str") -> int:
        """Return a numeric priority rank for sorting and escalation."""

        normalized = cls.normalize(value)
        order = {
            cls.LOW: 1,
            cls.NORMAL: 2,
            cls.HIGH: 3,
            cls.CRITICAL: 4,
            cls.EMERGENCY: 5,
        }
        return order.get(normalized, 2)

    @classmethod
    def normalize(cls, value: "NotificationPriority | str | None") -> "NotificationPriority":
        """Return a normalized enum value."""

        if isinstance(value, cls):
            return value
        text = str(value or "NORMAL").strip().upper()
        try:
            return cls[text]
        except Exception:
            return cls.NORMAL
