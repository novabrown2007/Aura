"""Spotify search result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SpotifySearchResult:
    """Structured Spotify search output."""

    query: str
    tracks: list[dict[str, object]] = field(default_factory=list)
    playlists: list[dict[str, object]] = field(default_factory=list)
    artists: list[dict[str, object]] = field(default_factory=list)
    albums: list[dict[str, object]] = field(default_factory=list)
    source: str = "mock"
    timestamp: str = field(default_factory=_utcNow)
    metadata: dict[str, object] = field(default_factory=dict)

    def asDict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "tracks": list(self.tracks or []),
            "playlists": list(self.playlists or []),
            "artists": list(self.artists or []),
            "albums": list(self.albums or []),
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata or {}),
        }
