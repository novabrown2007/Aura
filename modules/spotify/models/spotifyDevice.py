"""Spotify device model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpotifyDevice:
    """Describe one active Spotify playback target."""

    deviceId: str
    name: str
    type: str = "computer"
    isActive: bool = False
    isRestricted: bool = False
    volume: int = 100
    metadata: dict[str, object] = field(default_factory=dict)

    def asDict(self) -> dict[str, object]:
        return {
            "deviceId": self.deviceId,
            "name": self.name,
            "type": self.type,
            "isActive": bool(self.isActive),
            "isRestricted": bool(self.isRestricted),
            "volume": int(self.volume or 0),
            "metadata": dict(self.metadata or {}),
        }
