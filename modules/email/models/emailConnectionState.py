"""Supported email connection states."""

from __future__ import annotations


class EmailConnectionState:
    """Connection state helper for provider/session management."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    ERROR = "ERROR"

    @classmethod
    def normalize(cls, value) -> str:
        text = str(value or "").strip().upper()
        if text in {cls.DISCONNECTED, cls.CONNECTING, cls.CONNECTED, cls.AUTH_EXPIRED, cls.ERROR}:
            return text
        return cls.DISCONNECTED
