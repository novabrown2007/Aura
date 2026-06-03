"""Spotify state snapshot manager."""

from __future__ import annotations

from modules.spotify.models import SpotifyPlaybackState


class SpotifyStateManager:
    """Track the latest playback snapshot for Aura visibility."""

    def __init__(self, context=None, provider=None):
        self.context = context
        self.provider = provider
        self.lastPlaybackState = SpotifyPlaybackState()

    def initialize(self, context=None, provider=None):
        if context is not None:
            self.context = context
        if provider is not None:
            self.provider = provider
        self.refresh()
        return self

    def refresh(self):
        if self.provider is not None:
            try:
                snapshot = self.provider.getCurrentPlayback()
            except Exception:
                return self.lastPlaybackState
            self.lastPlaybackState = snapshot if isinstance(snapshot, SpotifyPlaybackState) else SpotifyPlaybackState(**getattr(snapshot, "asDict", lambda: dict(snapshot))())
        return self.lastPlaybackState

    def snapshot(self):
        payload = self.lastPlaybackState.asDict()
        track = str(payload.get("track") or "").strip()
        artist = str(payload.get("artist") or "").strip()
        payload["currentTrack"] = f"{artist} - {track}".strip(" -") if artist else (track or "Unknown track")
        return payload

    def setState(self, state):
        if isinstance(state, SpotifyPlaybackState):
            self.lastPlaybackState = state
        else:
            self.lastPlaybackState = SpotifyPlaybackState(**dict(state or {}))
        return self.lastPlaybackState

    def describe(self):
        playback = self.lastPlaybackState
        if playback.track:
            return f"{playback.artist or 'Unknown artist'} - {playback.track}"
        return "Nothing playing"
