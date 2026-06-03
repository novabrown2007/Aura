"""Spotify playback monitor."""

from __future__ import annotations

from modules.spotify.events import SpotifyEvents


class SpotifyPlaybackMonitor:
    """Detect playback changes and notify the assistant runtime."""

    def __init__(self, context=None, provider=None, stateManager=None):
        self.context = context
        self.provider = provider
        self.stateManager = stateManager
        self._lastSnapshot = None

    def initialize(self, context=None, provider=None, stateManager=None):
        if context is not None:
            self.context = context
        if provider is not None:
            self.provider = provider
        if stateManager is not None:
            self.stateManager = stateManager
        self._lastSnapshot = self.snapshot()
        return self

    def poll(self):
        snapshot = self.snapshot()
        if snapshot != self._lastSnapshot:
            self._emit(SpotifyEvents.TRACK_CHANGED, snapshot)
            if snapshot.get("isPlaying"):
                self._emit(SpotifyEvents.PLAYBACK_STARTED, snapshot)
            else:
                self._emit(SpotifyEvents.PLAYBACK_PAUSED, snapshot)
            self._lastSnapshot = snapshot
        return snapshot

    def snapshot(self):
        if self.stateManager is not None:
            return dict(self.stateManager.snapshot())
        if self.provider is not None:
            try:
                state = self.provider.getCurrentPlayback()
            except Exception:
                return {}
            return state.asDict() if hasattr(state, "asDict") else dict(state or {})
        return {}

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})
