"""Spotify playback state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SpotifyPlaybackState:
    """Track the current playback state Aura should surface."""

    track: str = ""
    artist: str = ""
    album: str = ""
    duration: int = 0
    progress: int = 0
    isPlaying: bool = False
    volume: int = 100
    playbackSpeed: float = 1.0
    shuffleEnabled: bool = False
    repeatMode: str = "off"
    activeDevice: str = ""
    playlist: str = ""
    timestamp: str = field(default_factory=_utcNow)
    source: str = "mock"
    metadata: dict[str, object] = field(default_factory=dict)

    def asDict(self) -> dict[str, object]:
        return {
            "track": self.track,
            "artist": self.artist,
            "album": self.album,
            "duration": int(self.duration or 0),
            "progress": int(self.progress or 0),
            "isPlaying": bool(self.isPlaying),
            "volume": int(self.volume or 0),
            "playbackSpeed": float(self.playbackSpeed or 1.0),
            "shuffleEnabled": bool(self.shuffleEnabled),
            "repeatMode": self.repeatMode,
            "activeDevice": self.activeDevice,
            "playlist": self.playlist,
            "timestamp": self.timestamp,
            "source": self.source,
            "metadata": dict(self.metadata or {}),
        }
