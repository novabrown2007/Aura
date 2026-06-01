"""Spotify connection state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SpotifyConnectionState:
    """Describe the current Spotify session state."""

    status: str = "DISCONNECTED"
    accessToken: str = ""
    refreshToken: str = ""
    expiresAt: str = ""
    connectedAt: str = ""
    lastError: str = ""
    userName: str = ""
    deviceName: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def isConnected(self) -> bool:
        return self.status.upper() == "CONNECTED"

    def asDict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "accessToken": self.accessToken,
            "refreshToken": self.refreshToken,
            "expiresAt": self.expiresAt,
            "connectedAt": self.connectedAt,
            "lastError": self.lastError,
            "userName": self.userName,
            "deviceName": self.deviceName,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def connected(cls, **kwargs):
        state = cls(status="CONNECTED", connectedAt=kwargs.pop("connectedAt", _utcNow()), **kwargs)
        return state
