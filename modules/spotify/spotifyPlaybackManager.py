"""Spotify playback command manager."""

from __future__ import annotations

from modules.spotify.events import SpotifyEvents


class SpotifyPlaybackManager:
    """Coordinate play/pause/seek/volume/speed commands."""

    def __init__(self, context=None, provider=None, stateManager=None):
        self.context = context
        self.provider = provider
        self.stateManager = stateManager

    def initialize(self, context=None, provider=None, stateManager=None):
        if context is not None:
            self.context = context
        if provider is not None:
            self.provider = provider
        if stateManager is not None:
            self.stateManager = stateManager
        return self

    def playTrack(self, **kwargs):
        state = self.provider.playTrack(**kwargs)
        self._sync(state)
        payload = self._withCompatibility(state.asDict())
        self._emit(SpotifyEvents.PLAYBACK_STARTED, payload)
        self._emitTrackChanged(payload)
        return payload

    def pause(self):
        state = self.provider.pause()
        self._sync(state)
        payload = self._withCompatibility(state.asDict())
        self._emit(SpotifyEvents.PLAYBACK_PAUSED, payload)
        return payload

    def resume(self):
        state = self.provider.resume()
        self._sync(state)
        payload = self._withCompatibility(state.asDict())
        self._emit(SpotifyEvents.PLAYBACK_STARTED, payload)
        return payload

    def nextTrack(self):
        state = self.provider.nextTrack()
        self._sync(state)
        payload = self._withCompatibility(state.asDict())
        self._emitTrackChanged(payload)
        return payload

    def previousTrack(self):
        state = self.provider.previousTrack()
        self._sync(state)
        payload = self._withCompatibility(state.asDict())
        self._emitTrackChanged(payload)
        return payload

    def seek(self, positionMs: int | None = None, offsetMs: int | None = None):
        if positionMs is not None:
            state = self.provider.seek(positionMs)
        else:
            state = self.provider.seekBy(offsetMs or 0)
        self._sync(state)
        return self._withCompatibility(state.asDict())

    def setPlaybackSpeed(self, speed: float):
        state = self.provider.setPlaybackSpeed(speed)
        self._sync(state)
        return self._withCompatibility(state.asDict())

    def setVolume(self, volume: int):
        state = self.provider.setVolume(volume)
        self._sync(state)
        return self._withCompatibility(state.asDict())

    def getPlaybackState(self):
        state = self.provider.getCurrentPlayback()
        self._sync(state)
        return self._withCompatibility(state.asDict())

    def _sync(self, state):
        if self.stateManager is not None:
            self.stateManager.setState(state)

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})

    def _emitTrackChanged(self, payload: dict[str, object]):
        self._emit(SpotifyEvents.TRACK_CHANGED, payload)

    @staticmethod
    def _withCompatibility(payload: dict[str, object]):
        result = dict(payload or {})
        currentTrack = result.get("currentTrack")
        if not currentTrack:
            artist = str(result.get("artist") or "").strip()
            track = str(result.get("track") or "").strip()
            if artist and track:
                currentTrack = f"{artist} - {track}"
            else:
                currentTrack = track or "Unknown track"
        result["currentTrack"] = currentTrack
        return result
