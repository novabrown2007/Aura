"""Central Spotify orchestration manager."""

from __future__ import annotations

from datetime import datetime, timezone

from modules.spotify.events import SpotifyEvents
from modules.spotify.models import SpotifyPlaybackState
from modules.spotify.providers import SpotifyApiProvider
from modules.spotify.spotifyActionExecutor import SpotifyActionExecutor
from modules.spotify.spotifyConnectionManager import SpotifyConnectionManager
from modules.spotify.spotifyDeviceManager import SpotifyDeviceManager
from modules.spotify.spotifyPlaybackManager import SpotifyPlaybackManager
from modules.spotify.spotifyPlaybackMonitor import SpotifyPlaybackMonitor
from modules.spotify.spotifyPlaylistManager import SpotifyPlaylistManager
from modules.spotify.spotifyQueueManager import SpotifyQueueManager
from modules.spotify.spotifySearchManager import SpotifySearchManager
from modules.spotify.spotifyStateManager import SpotifyStateManager
from modules.spotify.storage import SpotifyCacheStore
from modules.spotify.ui import SpotifyNowPlayingView, SpotifyOverlayWidget, SpotifyPlaybackControls, SpotifyPlaylistView


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


class SpotifyManager:
    """Coordinate Spotify playback, search, devices, and responses."""

    def __init__(self, context=None):
        self.context = context
        self.cacheStore = SpotifyCacheStore(self._readConfig("spotify.cachePath", "spotify_cache.sqlite3")) if self._readConfig("spotifyCacheEnabled", True) else None
        self.provider = SpotifyApiProvider(context, cacheStore=self.cacheStore)
        self.connectionManager = SpotifyConnectionManager(context, self.provider)
        self.stateManager = SpotifyStateManager(context, self.provider)
        self.playbackManager = SpotifyPlaybackManager(context, self.provider, self.stateManager)
        self.deviceManager = SpotifyDeviceManager(context, self.provider)
        self.searchManager = SpotifySearchManager(context, self.provider, self.cacheStore)
        self.playlistManager = SpotifyPlaylistManager(context, self.provider, self.cacheStore)
        self.queueManager = SpotifyQueueManager()
        self.actionExecutor = SpotifyActionExecutor(self)
        self.playbackMonitor = SpotifyPlaybackMonitor(context, self.provider, self.stateManager)
        self.initialized = False

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self.provider.initialize(self.context)
        self.connectionManager.initialize(self.context)
        self.stateManager.initialize(self.context, self.provider)
        self.playbackManager.initialize(self.context, self.provider, self.stateManager)
        self.deviceManager.initialize(self.context, self.provider)
        self.searchManager.initialize(self.context, self.provider, self.cacheStore)
        self.playlistManager.initialize(self.context, self.provider, self.cacheStore)
        self.playbackMonitor.initialize(self.context, self.provider, self.stateManager)
        self.initialized = True
        return self

    def shutdown(self):
        self.connectionManager.shutdown()

    def connect(self, interactive: bool = False):
        return self.connectionManager.connect(interactive=interactive)

    def disconnect(self, reason: str = ""):
        return self.connectionManager.disconnect(reason)

    def handleEvent(self, event):
        name = getattr(event, "name", "") if not isinstance(event, dict) else event.get("name", "")
        data = getattr(event, "data", {}) if not isinstance(event, dict) else event.get("data", {})
        if name == "system.started":
            self.connectionManager.ensureConnected()
            self.playbackMonitor.poll()
        elif name == "overlay.opened":
            self.playbackMonitor.poll()
        elif name == "voice.command.received":
            if isinstance(data, dict) and str(data.get("text") or "").lower().strip() in {"what song is playing", "what's playing", "what is playing"}:
                self.playbackMonitor.poll()
        return self.snapshot()

    def getConnectionState(self):
        return self.connectionManager.getState().asDict()

    def getPlaybackState(self):
        return self.stateManager.snapshot()

    def getNowPlaying(self):
        return self.stateManager.snapshot()

    def getCurrentTrack(self):
        return self.stateManager.snapshot()

    def playSong(self, track: str = "", artist: str = "", playlist: str = "", query: str = ""):
        payload = self.playbackManager.playTrack(trackId=track, query=query or track, playlistId=playlist, artist=artist)
        self._responseForPlayback(payload, action="spotify.playTrack")
        return payload

    def pauseMusic(self):
        payload = self.playbackManager.pause()
        self._responseForPlayback(payload, action="spotify.pause")
        return payload

    def resumeMusic(self):
        payload = self.playbackManager.resume()
        self._responseForPlayback(payload, action="spotify.resume")
        return payload

    def nextTrack(self):
        payload = self.playbackManager.nextTrack()
        self._responseForPlayback(payload, action="spotify.nextTrack")
        return payload

    def previousTrack(self):
        payload = self.playbackManager.previousTrack()
        self._responseForPlayback(payload, action="spotify.previousTrack")
        return payload

    def seekPlayback(self, positionMs: int | None = None, offsetMs: int | None = None):
        payload = self.playbackManager.seek(positionMs=positionMs, offsetMs=offsetMs)
        self._responseForPlayback(payload, action="spotify.seek")
        return payload

    def seekForward(self, seconds: int = 30):
        return self.seekPlayback(offsetMs=int(seconds) * 1000)

    def seekBackward(self, seconds: int = 30):
        return self.seekPlayback(offsetMs=-int(seconds) * 1000)

    def setPlaybackSpeed(self, speed: float):
        payload = self.playbackManager.setPlaybackSpeed(speed)
        self._responseForPlayback(payload, action="spotify.setPlaybackSpeed")
        return payload

    def setVolume(self, volume: int):
        payload = self.playbackManager.setVolume(volume)
        self._responseForPlayback(payload, action="spotify.setVolume")
        return payload

    def searchTracks(self, query: str = ""):
        return self.searchManager.searchTracks(query).copy()

    def searchPlaylists(self, query: str = ""):
        return self.searchManager.searchPlaylists(query).copy()

    def searchArtists(self, query: str = ""):
        return self.searchManager.searchArtists(query).copy()

    def searchAlbums(self, query: str = ""):
        return self.searchManager.searchAlbums(query).copy()

    def playPlaylist(self, playlistId: str = "", query: str = "", shuffle: bool = False):
        payload = self.playlistManager.playPlaylist(playlistId=playlistId, query=query, shuffle=shuffle)
        self.stateManager.setState(payload)
        self._responseForPlayback(payload, action="spotify.playPlaylist")
        return payload

    def listPlaylists(self):
        return self.playlistManager.listPlaylists()

    def listDevices(self):
        return self.deviceManager.listDevices()

    def transferPlayback(self, deviceId: str = ""):
        payload = self.deviceManager.transferPlayback(deviceId)
        self._responseForPlayback(payload, action="spotify.transferPlayback")
        self._notify("Playback transferred", f"Playback moved to {payload.get('activeDevice') or 'another device'}.", "NORMAL")
        return payload

    def getDashboard(self):
        try:
            playlists = self.listPlaylists()
        except Exception:
            playlists = []
        try:
            devices = self.listDevices()
        except Exception:
            devices = []
        return {
            "connection": self.getConnectionState(),
            "playback": self.getPlaybackState(),
            "devices": devices,
            "playlists": playlists,
            "queue": self.queueManager.listQueue(),
        }

    def snapshot(self):
        return self.getDashboard()

    def buildResponse(self, action: str = "", payload: dict[str, object] | None = None):
        payload = dict(payload or {})
        spoken = self._spokenText(payload)
        if action == "spotify.pause":
            spoken = "Playback paused."
        elif action == "spotify.transferPlayback":
            spoken = f"Playback transferred to {payload.get('activeDevice') or 'another device'}."
        elif action == "spotify.seek":
            spoken = "Playback position updated."
        elif action == "spotify.setVolume":
            spoken = f"Volume set to {int(payload.get('volume') or 0)} percent."
        elif action == "spotify.setPlaybackSpeed":
            spoken = f"Playback speed set to {payload.get('playbackSpeed') or 1.0}x."
        nowPlaying = self.stateManager.snapshot()
        uiText = self._uiText(nowPlaying, payload)
        notifications = []
        if not nowPlaying.get("isPlaying") and nowPlaying.get("track"):
            notifications.append({"title": "Spotify paused", "message": nowPlaying.get("track"), "priority": "LOW"})
        return {
            "spokenText": spoken,
            "uiText": uiText,
            "notifications": notifications,
            "actions": [action] if action else [],
            "metadata": {
                "provider": "spotify",
                "action": action,
                "timestamp": _utcNow(),
            },
        }

    def getOverlayWidget(self):
        return SpotifyOverlayWidget(self.stateManager.snapshot(), self.listPlaylists()).render()

    def getNowPlayingView(self):
        return SpotifyNowPlayingView(self.stateManager.snapshot()).render()

    def getPlaybackControls(self):
        return SpotifyPlaybackControls(self.stateManager.snapshot()).render()

    def getPlaylistView(self):
        return SpotifyPlaylistView(self.listPlaylists()).render()

    def _responseForPlayback(self, payload: dict[str, object], action: str):
        self._emit(SpotifyEvents.REQUESTED, {"action": action, "payload": dict(payload or {})})
        if payload.get("isPlaying"):
            self._emit(SpotifyEvents.PLAYBACK_STARTED, payload)
        else:
            self._emit(SpotifyEvents.PLAYBACK_PAUSED, payload)
        self._emit(SpotifyEvents.TRACK_CHANGED, payload)
        return self.buildResponse(action=action, payload=payload)

    def _spokenText(self, payload: dict[str, object]):
        tracks = payload.get("tracks") or []
        playlists = payload.get("playlists") or []
        devices = payload.get("devices") or []
        if tracks:
            return f"I found {len(tracks)} track{'' if len(tracks) == 1 else 's'}."
        if playlists:
            return f"I found {len(playlists)} playlist{'' if len(playlists) == 1 else 's'}."
        if devices and not payload.get("track"):
            return f"Available devices: {', '.join(str(device.get('name') or 'Unknown') for device in devices[:3])}."
        track = str(payload.get("track") or "").strip()
        artist = str(payload.get("artist") or "").strip()
        if track and artist:
            return f"Playing {track} by {artist}."
        if track:
            return f"Playing {track}."
        if not payload.get("isPlaying"):
            return "Playback paused."
        return "Spotify updated."

    def _uiText(self, playback: dict[str, object], payload: dict[str, object]):
        if payload.get("tracks") or payload.get("playlists") or payload.get("devices"):
            lines = [f"{payload.get('query') or 'Results'}"]
            for collectionName in ("tracks", "playlists", "devices", "artists", "albums"):
                collection = payload.get(collectionName) or []
                if not collection:
                    continue
                lines.append("")
                lines.append(collectionName.capitalize() + ":")
                for item in collection[:5]:
                    if isinstance(item, dict):
                        label = item.get("title") or item.get("name") or item.get("artist") or "Unknown"
                        subtitle = item.get("artist") or item.get("description") or item.get("type") or ""
                        lines.append(f"- {label}" + (f" ({subtitle})" if subtitle else ""))
            return "\n".join(lines)
        lines = [
            f"Now playing: {playback.get('track') or 'Nothing'}",
            f"Artist: {playback.get('artist') or 'Unknown'}",
            f"Album: {playback.get('album') or 'Unknown'}",
            f"Progress: {int(playback.get('progress') or 0)} / {int(playback.get('duration') or 0)} ms",
            f"Device: {playback.get('activeDevice') or 'Unknown'}",
            f"State: {'Playing' if playback.get('isPlaying') else 'Paused'}",
        ]
        if payload.get("playlist"):
            lines.append(f"Playlist: {payload.get('playlist')}")
        if payload.get("playbackSpeed"):
            lines.append(f"Speed: {payload.get('playbackSpeed')}x")
        return "\n".join(lines)

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})

    def _notify(self, title: str, message: str, priority: str):
        notificationManager = getattr(self.context, "notificationManager", None)
        if notificationManager is None or not hasattr(notificationManager, "createNotification"):
            return None
        try:
            return notificationManager.createNotification(
                {
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "category": "MEDIA",
                    "source": "spotify",
                },
                eventName="spotify.notification",
            )
        except Exception:
            return None

    def _readConfig(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
