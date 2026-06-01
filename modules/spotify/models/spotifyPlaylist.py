"""Spotify playlist model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpotifyPlaylist:
    """Describe a Spotify playlist."""

    playlistId: str
    name: str
    description: str = ""
    tracks: list[str] = field(default_factory=list)
    uri: str = ""
    isUserOwned: bool = True
    isFavorite: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def asDict(self) -> dict[str, object]:
        return {
            "playlistId": self.playlistId,
            "name": self.name,
            "description": self.description,
            "tracks": list(self.tracks or []),
            "uri": self.uri,
            "isUserOwned": bool(self.isUserOwned),
            "isFavorite": bool(self.isFavorite),
            "metadata": dict(self.metadata or {}),
        }
