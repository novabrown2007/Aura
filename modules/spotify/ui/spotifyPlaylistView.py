"""Playlist browser payload for the desktop overlay."""

from __future__ import annotations


class SpotifyPlaylistView:
    """Render available playlists into a UI-friendly structure."""

    def __init__(self, playlists=None):
        self.playlists = playlists or []

    def render(self):
        playlists = []
        for playlist in self.playlists or []:
            if hasattr(playlist, "asDict"):
                playlists.append(playlist.asDict())
            else:
                playlists.append(dict(playlist or {}))
        return {
            "playlists": playlists,
            "count": len(playlists),
        }
