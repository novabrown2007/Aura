"""Spotify search helper."""

from __future__ import annotations


class SpotifySearchManager:
    """Expose structured track, playlist, artist, and album search."""

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

    def searchTracks(self, query: str):
        cached = self._load("tracks", query)
        if cached is not None:
            return cached
        result = self.provider.searchTracks(query).asDict()
        self._save("tracks", query, result)
        self._emit(result)
        return result

    def searchPlaylists(self, query: str):
        cached = self._load("playlists", query)
        if cached is not None:
            return cached
        result = self.provider.searchPlaylists(query).asDict()
        self._save("playlists", query, result)
        self._emit(result)
        return result

    def searchArtists(self, query: str):
        return self.provider.searchArtists(query).asDict()

    def searchAlbums(self, query: str):
        return self.provider.searchAlbums(query).asDict()

    def _save(self, kind: str, query: str, payload: dict[str, object]):
        if self.cacheStore is None:
            return
        key = f"{kind}:{str(query or '').lower().strip()}"
        self.cacheStore.saveSearchResult(key, payload)

    def _load(self, kind: str, query: str):
        if self.cacheStore is None:
            return None
        key = f"{kind}:{str(query or '').lower().strip()}"
        return self.cacheStore.loadSearchResult(key)

    def _emit(self, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit("spotify.search.performed", payload or {})
