"""Spotify playlist manager."""

from __future__ import annotations

from modules.spotify.events import SpotifyEvents


class SpotifyPlaylistManager:
    """Manage saved playlists and playlist playback."""

    def __init__(self, context=None, provider=None, cacheStore=None):
        self.context = context
        self.provider = provider
        self.cacheStore = cacheStore

    def initialize(self, context=None, provider=None, cacheStore=None):
        if context is not None:
            self.context = context
        if provider is not None:
            self.provider = provider
        if cacheStore is not None:
            self.cacheStore = cacheStore
        return self

    def listPlaylists(self):
        playlists = self.provider.listPlaylists()
        if self.cacheStore is not None:
            self.cacheStore.savePlaylists(playlists)
        return playlists

    def playPlaylist(self, playlistId: str = "", query: str = "", shuffle: bool = False):
        state = self.provider.playPlaylist(playlistId=playlistId, query=query, shuffle=shuffle)
        self._emit(SpotifyEvents.PLAYLIST_CHANGED, {"playlist": state.playlist, **state.asDict()})
        self._emit(SpotifyEvents.PLAYBACK_STARTED, state.asDict())
        return state.asDict()

    def getPlaylist(self, playlistId: str = "", query: str = ""):
        for playlist in self.listPlaylists():
            if playlist.get("playlistId") == playlistId or playlist.get("uri") == playlistId:
                return playlist
        lowered = str(query or "").lower()
        for playlist in self.listPlaylists():
            if lowered and lowered in str(playlist.get("name", "")).lower():
                return playlist
        return None

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})
