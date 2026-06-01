"""Overlay summary for Spotify presence."""

from __future__ import annotations

from modules.spotify.ui.spotifyNowPlayingView import SpotifyNowPlayingView


class SpotifyOverlayWidget:
    """Build the compact overlay payload shown in the Windows shell."""

    def __init__(self, playbackState=None, playlists=None):
        self.playbackState = playbackState or {}
        self.playlists = playlists or []

    def render(self):
        nowPlaying = SpotifyNowPlayingView(self.playbackState).render()
        return {
            "nowPlaying": nowPlaying,
            "playlists": list(self.playlists or []),
            "compact": True,
        }
