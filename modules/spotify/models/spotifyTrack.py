"""Spotify track model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpotifyTrack:
    """Describe a Spotify track."""

    trackId: str
    title: str
    artist: str = ""
    album: str = ""
    durationMs: int = 0
    uri: str = ""
    albumArtUrl: str = ""
    explicit: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def displayName(self) -> str:
        return " - ".join(part for part in (self.artist, self.title) if part).strip(" -") or self.title or "Unknown track"

    def asDict(self) -> dict[str, object]:
        return {
            "trackId": self.trackId,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "durationMs": int(self.durationMs or 0),
            "uri": self.uri,
            "albumArtUrl": self.albumArtUrl,
            "explicit": bool(self.explicit),
            "metadata": dict(self.metadata or {}),
        }
