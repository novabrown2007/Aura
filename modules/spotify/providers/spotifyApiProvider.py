"""Deterministic Spotify provider abstraction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from modules.spotify.models import (
    SpotifyConnectionState,
    SpotifyDevice,
    SpotifyPlaybackState,
    SpotifyPlaylist,
    SpotifySearchResult,
    SpotifyTrack,
)
from modules.spotify.providers.spotifyWebApiClient import SpotifyWebApiClient


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


class SpotifyApiProvider:
    """Provider facade that can later wrap real Spotify APIs."""

    SUPPORTED_SPEEDS = (0.5, 1.0, 1.25, 1.5, 2.0)

    def __init__(self, context=None, cacheStore=None):
        self.context = context
        self.cacheStore = cacheStore
        self.connectionState = SpotifyConnectionState()
        self.playbackState = SpotifyPlaybackState()
        self.webClient: SpotifyWebApiClient | None = None
        self.devices = self._seedDevices()
        self.playlists = self._seedPlaylists()
        self.tracks = self._seedTracks()
        self._currentPlaylistId = ""
        self._history: list[str] = []
        self._connected = False
        self._demoMode = True

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self.webClient = SpotifyWebApiClient(self.context).initialize(self.context)
        self._demoMode = not self.webClient.isConfigured()
        self.connect()
        return self

    def isAvailable(self):
        return bool(self._connected or self.connectionState.isConnected() or (self.webClient and self.webClient.tokens.is_valid()))

    def connect(self, interactive: bool = False):
        if self.webClient is not None and self.webClient.isConfigured():
            try:
                remoteState = self.webClient.connect(interactive=bool(interactive))
                self.connectionState = SpotifyConnectionState(
                    status=str(remoteState.get("status") or "CONNECTED"),
                    accessToken=str(remoteState.get("accessToken") or ""),
                    refreshToken=str(remoteState.get("refreshToken") or ""),
                    expiresAt=str(remoteState.get("expiresAt") or ""),
                    connectedAt=str(remoteState.get("connectedAt") or _utcNow()),
                    lastError=str(remoteState.get("lastError") or ""),
                    userName=str(remoteState.get("userName") or ""),
                    deviceName=str(remoteState.get("deviceName") or ""),
                    metadata=dict(remoteState.get("metadata") or {}),
                )
                self._connected = self.connectionState.isConnected()
                if self._connected:
                    self._syncPlaybackFromRemote()
                return self.connectionState
            except Exception as error:
                self.connectionState = SpotifyConnectionState(
                    status="DISCONNECTED",
                    lastError=str(error),
                    metadata={"mode": "webapi"},
                )
                self._connected = False
                return self.connectionState

        token = self._readConfig("spotify.api.accessToken", "") or self._readConfig("spotify.accessToken", "")
        refreshToken = self._readConfig("spotify.api.refreshToken", "") or self._readConfig("spotify.refreshToken", "")
        userName = self._readConfig("spotify.userName", "") or "Aura"
        deviceName = self._readConfig("spotify.defaultDevice", "") or "Desktop"
        self.connectionState = SpotifyConnectionState.connected(
            accessToken=str(token or "demo-token"),
            refreshToken=str(refreshToken or "demo-refresh-token"),
            expiresAt=_utcNow(),
            userName=str(userName),
            deviceName=str(deviceName),
            metadata={"mode": "demo" if self._demoMode else "api"},
        )
        self._connected = True
        return self.connectionState

    def disconnect(self, reason: str = ""):
        if self.webClient is not None and self.webClient.isConfigured():
            remoteState = self.webClient.disconnect(reason)
            self.connectionState = SpotifyConnectionState(
                status=str(remoteState.get("status") or "DISCONNECTED"),
                accessToken=str(remoteState.get("accessToken") or ""),
                refreshToken=str(remoteState.get("refreshToken") or ""),
                expiresAt=str(remoteState.get("expiresAt") or ""),
                connectedAt=str(remoteState.get("connectedAt") or ""),
                lastError=str(remoteState.get("lastError") or reason or ""),
                userName=str(remoteState.get("userName") or ""),
                deviceName=str(remoteState.get("deviceName") or ""),
                metadata=dict(remoteState.get("metadata") or {}),
            )
            self._connected = False
            return self.connectionState
        self._connected = False
        self.connectionState = SpotifyConnectionState(
            status="DISCONNECTED",
            lastError=str(reason or ""),
            metadata={"mode": "demo" if self._demoMode else "api"},
        )
        return self.connectionState

    def refreshToken(self):
        if self.webClient is not None and self.webClient.isConfigured():
            remoteState = self.webClient.refreshToken()
            self.connectionState = SpotifyConnectionState(
                status=str(remoteState.get("status") or "CONNECTED"),
                accessToken=str(remoteState.get("accessToken") or ""),
                refreshToken=str(remoteState.get("refreshToken") or ""),
                expiresAt=str(remoteState.get("expiresAt") or ""),
                connectedAt=str(remoteState.get("connectedAt") or _utcNow()),
                lastError=str(remoteState.get("lastError") or ""),
                userName=str(remoteState.get("userName") or ""),
                deviceName=str(remoteState.get("deviceName") or ""),
                metadata=dict(remoteState.get("metadata") or {}),
            )
            self._connected = self.connectionState.isConnected()
            return self.connectionState
        self.connectionState.expiresAt = _utcNow()
        self.connectionState.metadata["refreshed"] = True
        return self.connectionState

    def getConnectionState(self):
        return SpotifyConnectionState(**self.connectionState.asDict())

    def getCurrentPlayback(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return SpotifyPlaybackState(**self.webClient.getCurrentPlayback())
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        return SpotifyPlaybackState(**self.playbackState.asDict())

    def getNowPlaying(self):
        return self.getCurrentPlayback()

    def searchTracks(self, query: str):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return self.webClient.searchTracks(query)
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        result = self._search(query, self.tracks)
        payload = SpotifySearchResult(query=query, tracks=[track.asDict() for track in result], source="mock")
        self._cacheSearch(f"tracks:{query.lower().strip()}", payload.asDict())
        return payload

    def searchPlaylists(self, query: str):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return self.webClient.searchPlaylists(query)
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        result = self._search(query, self.playlists)
        payload = SpotifySearchResult(query=query, playlists=[playlist.asDict() for playlist in result], source="mock")
        self._cacheSearch(f"playlists:{query.lower().strip()}", payload.asDict())
        return payload

    def searchArtists(self, query: str):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return self.webClient.searchArtists(query)
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        artists = [{"artistId": artist, "name": artist} for artist in self._matchArtists(query)]
        return SpotifySearchResult(query=query, artists=artists, source="mock")

    def searchAlbums(self, query: str):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return self.webClient.searchAlbums(query)
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        albums = [{"albumId": album, "name": album} for album in self._matchAlbums(query)]
        return SpotifySearchResult(query=query, albums=albums, source="mock")

    def listPlaylists(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            playlists = self.webClient.listPlaylists()
            if self.cacheStore is not None:
                self.cacheStore.savePlaylists(playlists)
            return playlists
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        cached = self.cacheStore.loadPlaylists() if self.cacheStore else []
        return cached or [playlist.asDict() for playlist in self.playlists]

    def listDevices(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return self.webClient.listDevices()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        return [device.asDict() for device in self.devices]

    def setActiveDevice(self, deviceId: str):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.transferPlayback(deviceId)
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.playbackState
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        selected = None
        for device in self.devices:
            device.isActive = device.deviceId == deviceId
            if device.isActive:
                selected = device
        if selected is None and self.devices:
            selected = self.devices[0]
            selected.isActive = True
        self.playbackState.activeDevice = selected.name if selected else ""
        self.connectionState.deviceName = self.playbackState.activeDevice
        return self.playbackState

    def playTrack(self, trackId: str = "", query: str = "", playlistId: str = "", artist: str = "", playNow: bool = True):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.playTrack(trackId=trackId, query=query, playlistId=playlistId, artist=artist, playNow=playNow)
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        track = self._resolveTrack(trackId=trackId, query=query, playlistId=playlistId)
        if track is None:
            displayTitle = str(query or trackId or "Track")
            track = SpotifyTrack(
                trackId=trackId or f"track-{displayTitle.lower().replace(' ', '-')}",
                title=displayTitle,
                artist=str(artist or ""),
                album="",
                durationMs=180000,
                uri=f"spotify:track:{displayTitle.lower().replace(' ', '-')}",
            )
        self.playbackState.track = track.title
        self.playbackState.artist = track.artist
        self.playbackState.album = track.album
        self.playbackState.duration = int(track.durationMs or 0)
        self.playbackState.progress = 0
        self.playbackState.isPlaying = bool(playNow)
        self.playbackState.playlist = self._playlistNameForTrack(track.trackId, playlistId)
        self.playbackState.timestamp = _utcNow()
        self._history.append(track.trackId)
        self._cachePlayback("current", self.playbackState.asDict())
        self._cacheRecentTrack(track.trackId, track.asDict())
        if track.albumArtUrl:
            self._cacheAlbumArt(track.trackId, {"albumArtUrl": track.albumArtUrl, "title": track.title})
        return self.getCurrentPlayback()

    def playPlaylist(self, playlistId: str = "", query: str = "", shuffle: bool = False):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.playPlaylist(playlistId=playlistId, query=query, shuffle=shuffle)
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        playlist = self._resolvePlaylist(playlistId=playlistId, query=query)
        if playlist is None:
            playlist = self.playlists[0]
        if shuffle and playlist.tracks:
            playlist = SpotifyPlaylist(**playlist.asDict())
            playlist.tracks = list(reversed(playlist.tracks))
        self._currentPlaylistId = playlist.playlistId
        if playlist.tracks:
            return self.playTrack(trackId=playlist.tracks[0], playlistId=playlist.playlistId)
        self.playbackState.playlist = playlist.name
        self.playbackState.isPlaying = True
        self.playbackState.timestamp = _utcNow()
        return self.getCurrentPlayback()

    def pause(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.pause()
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        self.playbackState.isPlaying = False
        self.playbackState.timestamp = _utcNow()
        self._cachePlayback("current", self.playbackState.asDict())
        return self.getCurrentPlayback()

    def resume(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.resume()
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        self.playbackState.isPlaying = True
        self.playbackState.timestamp = _utcNow()
        self._cachePlayback("current", self.playbackState.asDict())
        return self.getCurrentPlayback()

    def nextTrack(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.nextTrack()
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        if not self._history:
            return self.playTrack()
        currentIndex = self._trackIndex(self._history[-1])
        nextIndex = min(currentIndex + 1, len(self.tracks) - 1)
        return self.playTrack(trackId=self.tracks[nextIndex].trackId, playlistId=self._currentPlaylistId)

    def previousTrack(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.previousTrack()
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        if not self._history:
            return self.playTrack()
        currentIndex = self._trackIndex(self._history[-1])
        previousIndex = max(currentIndex - 1, 0)
        return self.playTrack(trackId=self.tracks[previousIndex].trackId, playlistId=self._currentPlaylistId)

    def seek(self, positionMs: int):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.seek(positionMs)
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        positionMs = max(0, int(positionMs or 0))
        if self.playbackState.duration:
            positionMs = min(positionMs, int(self.playbackState.duration))
        self.playbackState.progress = positionMs
        self.playbackState.timestamp = _utcNow()
        self._cachePlayback("current", self.playbackState.asDict())
        return self.getCurrentPlayback()

    def seekBy(self, deltaMs: int):
        return self.seek(self.playbackState.progress + int(deltaMs or 0))

    def setVolume(self, volume: int):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.setVolume(volume)
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        self.playbackState.volume = max(0, min(100, int(volume or 0)))
        self.playbackState.timestamp = _utcNow()
        self._cachePlayback("current", self.playbackState.asDict())
        return self.getCurrentPlayback()

    def setPlaybackSpeed(self, speed: float):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            raise NotImplementedError("Spotify Web API does not expose playback speed control.")
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        requested = float(speed or 1.0)
        nearest = min(self.SUPPORTED_SPEEDS, key=lambda item: abs(item - requested))
        supported = abs(nearest - requested) < 0.26
        self.playbackState.playbackSpeed = nearest if supported else requested
        self.playbackState.metadata["playbackSpeedSupported"] = supported
        self.playbackState.timestamp = _utcNow()
        self._cachePlayback("current", self.playbackState.asDict())
        return self.getCurrentPlayback()

    def transferPlayback(self, deviceId: str):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            payload = self.webClient.transferPlayback(deviceId)
            self.playbackState = SpotifyPlaybackState(**payload)
            return self.getCurrentPlayback()
        if self.webClient is not None and self.webClient.isConfigured():
            raise RuntimeError("Spotify is not authenticated.")
        device = next((item for item in self.devices if item.deviceId == deviceId), None)
        if device is None:
            return self.getCurrentPlayback()
        for item in self.devices:
            item.isActive = item.deviceId == deviceId
        self.playbackState.activeDevice = device.name
        self.connectionState.deviceName = device.name
        self.playbackState.timestamp = _utcNow()
        return self.getCurrentPlayback()

    def snapshot(self):
        if self.webClient is not None and self.webClient.isConfigured() and self.webClient.tokens.is_valid():
            return self.webClient.snapshot()
        if self.webClient is not None and self.webClient.isConfigured():
            return {
                "connection": self.connectionState.asDict(),
                "playback": self.playbackState.asDict(),
                "devices": [],
                "playlists": [],
            }
        return {
            "connection": self.connectionState.asDict(),
            "playback": self.playbackState.asDict(),
            "devices": [device.asDict() for device in self.devices],
            "playlists": [playlist.asDict() for playlist in self.playlists],
        }

    def _syncPlaybackFromRemote(self):
        if self.webClient is None:
            return
        try:
            payload = self.webClient.getCurrentPlayback()
        except Exception:
            return
        self.playbackState = SpotifyPlaybackState(**payload)

    def shutdown(self):
        self.disconnect("shutdown")

    def _search(self, query: str, items):
        lowered = str(query or "").strip().lower()
        if not lowered:
            return list(items[:5])
        matched = []
        for item in items:
            haystack = " ".join(
                str(value).lower()
                for value in (
                    getattr(item, "title", ""),
                    getattr(item, "artist", ""),
                    getattr(item, "album", ""),
                    getattr(item, "name", ""),
                    getattr(item, "description", ""),
                )
            )
            score = sum(1 for token in lowered.split() if token in haystack)
            if score or lowered in haystack:
                matched.append((score, item))
        matched.sort(key=lambda pair: (-pair[0], getattr(pair[1], "name", getattr(pair[1], "title", ""))))
        return [item for _, item in matched[:10]]

    def _resolveTrack(self, trackId: str = "", query: str = "", playlistId: str = ""):
        if trackId:
            for track in self.tracks:
                if track.trackId == trackId or track.uri == trackId:
                    return track
        search = self.searchTracks(query) if query else None
        if search and search.tracks:
            selected = search.tracks[0]
            return next((track for track in self.tracks if track.trackId == selected["trackId"]), None)
        if playlistId:
            playlist = self._resolvePlaylist(playlistId=playlistId)
            if playlist and playlist.tracks:
                return self._resolveTrack(trackId=playlist.tracks[0])
        return None

    def _resolvePlaylist(self, playlistId: str = "", query: str = ""):
        if playlistId:
            for playlist in self.playlists:
                if playlist.playlistId == playlistId or playlist.uri == playlistId:
                    return playlist
        result = self.searchPlaylists(query) if query else None
        if result and result.playlists:
            selected = result.playlists[0]
            return next((playlist for playlist in self.playlists if playlist.playlistId == selected["playlistId"]), None)
        return None

    def _playlistNameForTrack(self, trackId: str, playlistId: str = ""):
        if playlistId:
            playlist = self._resolvePlaylist(playlistId=playlistId)
            if playlist:
                return playlist.name
        for playlist in self.playlists:
            if trackId in playlist.tracks:
                return playlist.name
        return self.playbackState.playlist

    def _trackIndex(self, trackId: str):
        for index, track in enumerate(self.tracks):
            if track.trackId == trackId:
                return index
        return 0

    def _cachePlayback(self, key: str, payload: dict[str, object]):
        if self.cacheStore is None:
            return
        try:
            self.cacheStore.savePlaybackSnapshot(key, payload)
        except Exception:
            pass

    def _cacheRecentTrack(self, trackId: str, payload: dict[str, object]):
        if self.cacheStore is None:
            return
        try:
            self.cacheStore.saveRecentTrack(trackId, payload)
        except Exception:
            pass

    def _cacheAlbumArt(self, key: str, payload: dict[str, object]):
        if self.cacheStore is None:
            return
        try:
            self.cacheStore.saveAlbumArtReference(key, payload)
        except Exception:
            pass

    def _cacheSearch(self, key: str, payload: dict[str, object]):
        if self.cacheStore is None:
            return
        try:
            self.cacheStore.saveSearchResult(key, payload)
        except Exception:
            pass

    def _readConfig(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    @staticmethod
    def _seedTracks():
        return [
            SpotifyTrack("track-coding-mix-1", "Coding Dreams", "Aura", "Coding Mix", 180000, "spotify:track:coding-dreams", metadata={"genre": "lofi"}),
            SpotifyTrack("track-coding-mix-2", "Deep Focus", "Aura", "Coding Mix", 210000, "spotify:track:deep-focus", metadata={"genre": "ambient"}),
            SpotifyTrack("track-rock-1", "Bohemian Rhapsody", "Queen", "A Night at the Opera", 354000, "spotify:track:bohemian-rhapsody"),
            SpotifyTrack("track-pop-1", "Blinding Lights", "The Weeknd", "After Hours", 200000, "spotify:track:blinding-lights"),
            SpotifyTrack("track-jazz-1", "Take Five", "The Dave Brubeck Quartet", "Time Out", 325000, "spotify:track:take-five"),
            SpotifyTrack("track-focus-1", "Lo-Fi Study", "Aura", "Focus Flow", 240000, "spotify:track:lofi-study"),
        ]

    @classmethod
    def _seedPlaylists(cls):
        return [
            SpotifyPlaylist("playlist-coding", "Coding Mix", "Focus music for deep work.", ["track-coding-mix-1", "track-coding-mix-2", "track-focus-1"], "spotify:playlist:coding", isFavorite=True),
            SpotifyPlaylist("playlist-lofi", "Lo-fi Focus", "Relaxed beats for study.", ["track-focus-1", "track-coding-mix-1"], "spotify:playlist:lofi", isFavorite=True),
            SpotifyPlaylist("playlist-rock", "Classic Rock", "Big guitar and big vocals.", ["track-rock-1"], "spotify:playlist:rock"),
        ]

    @classmethod
    def _seedDevices(cls):
        return [
            SpotifyDevice("device-desktop", "Desktop", "computer", isActive=True, volume=80),
            SpotifyDevice("device-phone", "Phone", "smartphone", isActive=False, volume=60),
            SpotifyDevice("device-web", "Web Player", "speaker", isActive=False, volume=70),
        ]

    @classmethod
    def _matchArtists(cls, query: str):
        lowered = str(query or "").lower()
        artists = {track.artist for track in cls._seedTracks()}
        return sorted(artist for artist in artists if lowered in artist.lower())

    @classmethod
    def _matchAlbums(cls, query: str):
        lowered = str(query or "").lower()
        albums = {track.album for track in cls._seedTracks()}
        return sorted(album for album in albums if lowered in album.lower())
