"""Aura Spotify capability module."""

from __future__ import annotations

from datetime import datetime, timezone

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata
from core.modules.base.moduleSubscription import ModuleSubscription
from core.modules.modulePermissions import ModulePermissions
from core.tools.tool import Tool
from modules.spotify.actions import SPOTIFY_ACTIONS, SPOTIFY_PLAYBACK_ACTIONS, SPOTIFY_PLAYLIST_ACTIONS
from modules.spotify.handlers import SpotifyEventHandler
from modules.spotify.intents import SPOTIFY_INTENTS
from modules.spotify.spotifyEvents import SpotifyEvents
from modules.spotify.spotifyManager import SpotifyManager
from modules.spotify.spotifyPermissions import SPOTIFY_PERMISSIONS


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


class SpotifyModule(AuraModule):
    """Unified media control module for Spotify playback and discovery."""

    metadata = ModuleMetadata(
        name="spotify",
        version="1.0.0",
        author="Aura",
        description="Unified Spotify connection, media, and playback control module.",
        permissions=tuple(SPOTIFY_PERMISSIONS.asList()),
        capabilities=(
            "spotify.playback",
            "spotify.search",
            "spotify.playlists",
            "spotify.devices",
            "spotify.queue",
            "spotify.seek",
            "spotify.volume",
            "spotify.speed",
            "spotify.control",
        ),
    )

    def __init__(self, context=None):
        super().__init__()
        self.manager: SpotifyManager | None = None
        self.eventHandler: SpotifyEventHandler | None = None
        self.permissions = SPOTIFY_PERMISSIONS
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        self.manager = SpotifyManager(context).initialize(context)
        self.eventHandler = SpotifyEventHandler(self.manager)
        self.permissions = SPOTIFY_PERMISSIONS
        self._logStartup("spotify module started.")
        return self

    def shutdown(self):
        if self.manager is not None:
            self.manager.shutdown()

    def startup(self):
        if self.manager is not None:
            self.manager.connectionManager.ensureConnected()
        return self

    def pause(self):
        if self.manager is not None:
            self.manager.pauseMusic()

    def resume(self):
        if self.manager is not None:
            self.manager.resumeMusic()

    def reload(self):
        if self.manager is not None:
            self.manager.initialize(self.context)
        return self

    def getIntents(self):
        return list(SPOTIFY_INTENTS)

    def getActions(self):
        return list((*SPOTIFY_ACTIONS, *SPOTIFY_PLAYBACK_ACTIONS, *SPOTIFY_PLAYLIST_ACTIONS))

    def getSubscriptions(self):
        return [
            ModuleSubscription(eventName="system.started", handler="handleEvent"),
            ModuleSubscription(eventName="overlay.opened", handler="handleEvent"),
            ModuleSubscription(eventName="voice.command.received", handler="handleEvent"),
        ]

    def getPermissions(self):
        return self.permissions

    def getTools(self):
        return [
            Tool(
                name="spotify.playTrack",
                description="Play a specific track or search result.",
                parameters={
                    "track": {"type": "string"},
                    "artist": {"type": "string"},
                    "playlist": {"type": "string"},
                    "query": {"type": "string"},
                },
                module="spotify",
                method="playTrack",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playback",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.pause",
                description="Pause playback.",
                parameters={},
                module="spotify",
                method="pausePlayback",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playback",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.nextTrack",
                description="Skip to the next track.",
                parameters={},
                module="spotify",
                method="nextTrack",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playback",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.previousTrack",
                description="Return to the previous track.",
                parameters={},
                module="spotify",
                method="previousTrack",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playback",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.seek",
                description="Seek to a playback position or offset.",
                parameters={"positionMs": {"type": "integer"}, "offsetMs": {"type": "integer"}},
                module="spotify",
                method="seekPlayback",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.seek",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.setPlaybackSpeed",
                description="Adjust playback speed.",
                parameters={"speed": {"type": "number"}},
                module="spotify",
                method="setPlaybackSpeed",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.speed",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.setVolume",
                description="Set playback volume.",
                parameters={"volume": {"type": "integer"}},
                module="spotify",
                method="setVolume",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.volume",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.searchTracks",
                description="Search tracks.",
                parameters={"query": {"type": "string"}},
                module="spotify",
                method="searchTracks",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.search",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.searchPlaylists",
                description="Search playlists.",
                parameters={"query": {"type": "string"}},
                module="spotify",
                method="searchPlaylists",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.search",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.playPlaylist",
                description="Play a playlist.",
                parameters={"playlistId": {"type": "string"}, "query": {"type": "string"}, "shuffle": {"type": "boolean"}},
                module="spotify",
                method="playPlaylist",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playlists", "spotify.playback"),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.getNowPlaying",
                description="Get the current now-playing payload.",
                parameters={},
                module="spotify",
                method="getNowPlaying",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playback",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.getPlaybackState",
                description="Get the current playback state snapshot.",
                parameters={},
                module="spotify",
                method="getPlaybackState",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playback",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.listDevices",
                description="List Spotify devices.",
                parameters={},
                module="spotify",
                method="listDevices",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.devices",),
                riskLevel="LOW",
            ),
            Tool(
                name="spotify.transferPlayback",
                description="Transfer playback to a different device.",
                parameters={"deviceId": {"type": "string"}},
                module="spotify",
                method="transferPlayback",
                safe=False,
                offlineAllowed=True,
                confirmRequired=True,
                requiredPermissions=("spotify.devices",),
                riskLevel="MODERATE",
            ),
            Tool(
                name="spotify.listPlaylists",
                description="List saved playlists.",
                parameters={},
                module="spotify",
                method="listPlaylists",
                safe=True,
                offlineAllowed=True,
                requiredPermissions=("spotify.playlists",),
                riskLevel="LOW",
            ),
        ]

    def handleEvent(self, event):
        if self.manager is None:
            return None
        return self.manager.handleEvent(event)

    def handleIntent(self, intent):
        intentName = getattr(intent, "name", intent)
        data = dict(getattr(intent, "data", {}) or getattr(intent, "arguments", {}) or {})
        if self.manager is None:
            return self._standaloneIntent(intentName, data)
        if intentName in {"spotify.play", "spotify.playTrack"}:
            payload = self.manager.playSong(
                track=str(data.get("track") or data.get("query") or ""),
                artist=str(data.get("artist") or ""),
                playlist=str(data.get("playlist") or data.get("playlistId") or ""),
                query=str(data.get("query") or data.get("track") or data.get("playlist") or ""),
            )
            return self.manager.buildResponse("spotify.playTrack", payload)
        if intentName == "spotify.pause":
            payload = self.manager.pauseMusic()
            return self.manager.buildResponse("spotify.pause", payload)
        if intentName == "spotify.next":
            payload = self.manager.nextTrack()
            return self.manager.buildResponse("spotify.nextTrack", payload)
        if intentName == "spotify.previous":
            payload = self.manager.previousTrack()
            return self.manager.buildResponse("spotify.previousTrack", payload)
        if intentName in {"spotify.search", "spotify.searchTracks"}:
            payload = self.manager.searchTracks(str(data.get("query") or data.get("track") or ""))
            return self.manager.buildResponse("spotify.searchTracks", payload)
        if intentName == "spotify.searchPlaylists":
            payload = self.manager.searchPlaylists(str(data.get("query") or ""))
            return self.manager.buildResponse("spotify.searchPlaylists", payload)
        if intentName == "spotify.playPlaylist":
            payload = self.manager.playPlaylist(
                playlistId=str(data.get("playlistId") or data.get("playlist") or ""),
                query=str(data.get("query") or data.get("playlist") or ""),
                shuffle=bool(data.get("shuffle", False)),
            )
            return self.manager.buildResponse("spotify.playPlaylist", payload)
        if intentName == "spotify.seek":
            payload = self.manager.seekPlayback(
                positionMs=self._coerceInt(data.get("positionMs")),
                offsetMs=self._coerceInt(data.get("offsetMs")),
            )
            return self.manager.buildResponse("spotify.seek", payload)
        if intentName == "spotify.speed":
            payload = self.manager.setPlaybackSpeed(float(data.get("speed") or 1.0))
            return self.manager.buildResponse("spotify.setPlaybackSpeed", payload)
        if intentName == "spotify.volume":
            payload = self.manager.setVolume(int(data.get("volume") or 0))
            return self.manager.buildResponse("spotify.setVolume", payload)
        if intentName == "spotify.nowPlaying":
            return self.manager.buildResponse("spotify.getNowPlaying", self.manager.getNowPlaying())
        if intentName == "spotify.getPlaybackState":
            return self.manager.buildResponse("spotify.getPlaybackState", self.manager.getPlaybackState())
        if intentName == "spotify.listDevices":
            return self.manager.buildResponse("spotify.listDevices", {"devices": self.manager.listDevices(), "isPlaying": self.manager.getPlaybackState().get("isPlaying", False)})
        if intentName == "spotify.transferDevice":
            payload = self.manager.transferPlayback(str(data.get("deviceId") or data.get("device") or ""))
            return self.manager.buildResponse("spotify.transferPlayback", payload)
        if intentName == "spotify.listPlaylists":
            return self.manager.buildResponse("spotify.listPlaylists", {"playlists": self.manager.listPlaylists(), "isPlaying": self.manager.getPlaybackState().get("isPlaying", False)})
        raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")

    def getCurrentTrack(self):
        return self.manager.getCurrentTrack() if self.manager is not None else self._fallbackPlayback("Nothing playing", isPlaying=False)

    def playTrack(self, track: str = "", artist: str = "", playlist: str = "", query: str = ""):
        if self.manager is None:
            return self._fallbackPlayback(track or query or "Track", artist=artist, playlist=playlist, isPlaying=True)
        return self.manager.playSong(track=track, artist=artist, playlist=playlist, query=query)

    def playSong(self, track: str = "", artist: str = "", playlist: str = "", query: str = ""):
        return self.playTrack(track=track, artist=artist, playlist=playlist, query=query)

    def pausePlayback(self):
        return self.pauseMusic()

    def pauseMusic(self):
        if self.manager is None:
            return self._fallbackPlayback(self.getCurrentTrack().get("track", "Track"), isPlaying=False)
        return self.manager.pauseMusic()

    def nextTrack(self):
        if self.manager is None:
            return self._fallbackPlayback("Next track", isPlaying=True)
        return self.manager.nextTrack()

    def previousTrack(self):
        if self.manager is None:
            return self._fallbackPlayback("Previous track", isPlaying=True)
        return self.manager.previousTrack()

    def seekPlayback(self, positionMs: int | None = None, offsetMs: int | None = None):
        if self.manager is None:
            return {"positionMs": positionMs, "offsetMs": offsetMs, "track": "Track", "isPlaying": True}
        return self.manager.seekPlayback(positionMs=positionMs, offsetMs=offsetMs)

    def seekForward(self, seconds: int = 30):
        if self.manager is None:
            return {"offsetMs": int(seconds) * 1000}
        return self.manager.seekForward(seconds)

    def seekBackward(self, seconds: int = 30):
        if self.manager is None:
            return {"offsetMs": -int(seconds) * 1000}
        return self.manager.seekBackward(seconds)

    def setPlaybackSpeed(self, speed: float):
        if self.manager is None:
            return {"playbackSpeed": float(speed), "track": "Track", "isPlaying": True}
        return self.manager.setPlaybackSpeed(speed)

    def setVolume(self, volume: int):
        if self.manager is None:
            return {"volume": max(0, min(100, int(volume or 0))), "track": "Track", "isPlaying": True}
        return self.manager.setVolume(volume)

    def searchTracks(self, query: str = ""):
        return self.manager.searchTracks(query) if self.manager is not None else self._fallbackSearch(query, "tracks")

    def searchPlaylists(self, query: str = ""):
        return self.manager.searchPlaylists(query) if self.manager is not None else self._fallbackSearch(query, "playlists")

    def searchArtists(self, query: str = ""):
        return self.manager.searchArtists(query) if self.manager is not None else self._fallbackSearch(query, "artists")

    def searchAlbums(self, query: str = ""):
        return self.manager.searchAlbums(query) if self.manager is not None else self._fallbackSearch(query, "albums")

    def playPlaylist(self, playlistId: str = "", query: str = "", shuffle: bool = False):
        if self.manager is None:
            return self._fallbackPlayback(query or playlistId or "Playlist", playlist=query or playlistId, isPlaying=True)
        return self.manager.playPlaylist(playlistId=playlistId, query=query, shuffle=shuffle)

    def listPlaylists(self):
        return self.manager.listPlaylists() if self.manager is not None else [{"playlistId": "playlist-coding", "name": "Coding Mix"}]

    def listDevices(self):
        return self.manager.listDevices() if self.manager is not None else [{"deviceId": "device-desktop", "name": "Desktop", "isActive": True}]

    def transferPlayback(self, deviceId: str = ""):
        if self.manager is None:
            return self._fallbackPlayback("Track", playlist="", isPlaying=True)
        return self.manager.transferPlayback(deviceId)

    def getPlaybackState(self):
        return self.manager.getPlaybackState() if self.manager is not None else self._fallbackPlayback("Track", isPlaying=False)

    def getNowPlaying(self):
        return self.getCurrentTrack()

    def getTools(self):
        return list(self._buildTools())

    def getOverlayWidget(self):
        return self.manager.getOverlayWidget() if self.manager is not None else {"compact": True, "nowPlaying": self.getCurrentTrack()}

    def getNowPlayingView(self):
        return self.manager.getNowPlayingView() if self.manager is not None else self.getCurrentTrack()

    def getPlaybackControls(self):
        return self.manager.getPlaybackControls() if self.manager is not None else {"canPlay": True, "canPause": True, "isPlaying": False}

    def getPlaylistView(self):
        return self.manager.getPlaylistView() if self.manager is not None else {"playlists": self.listPlaylists(), "count": len(self.listPlaylists())}

    def snapshot(self):
        if self.manager is not None:
            return self.manager.snapshot()
        return {"connection": {"status": "CONNECTED"}, "playback": self.getCurrentTrack(), "devices": self.listDevices(), "playlists": self.listPlaylists(), "queue": []}

    def _buildTools(self):
        return [
            Tool(name="spotify.playTrack", description="Play a specific track or search result.", parameters={"track": {"type": "string"}, "artist": {"type": "string"}, "playlist": {"type": "string"}, "query": {"type": "string"}}, module="spotify", method="playTrack", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playback",), riskLevel="LOW"),
            Tool(name="spotify.pause", description="Pause playback.", parameters={}, module="spotify", method="pausePlayback", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playback",), riskLevel="LOW"),
            Tool(name="spotify.nextTrack", description="Skip to the next track.", parameters={}, module="spotify", method="nextTrack", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playback",), riskLevel="LOW"),
            Tool(name="spotify.previousTrack", description="Return to the previous track.", parameters={}, module="spotify", method="previousTrack", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playback",), riskLevel="LOW"),
            Tool(name="spotify.seek", description="Seek to a playback position or offset.", parameters={"positionMs": {"type": "integer"}, "offsetMs": {"type": "integer"}}, module="spotify", method="seekPlayback", safe=True, offlineAllowed=True, requiredPermissions=("spotify.seek",), riskLevel="LOW"),
            Tool(name="spotify.setPlaybackSpeed", description="Adjust playback speed.", parameters={"speed": {"type": "number"}}, module="spotify", method="setPlaybackSpeed", safe=True, offlineAllowed=True, requiredPermissions=("spotify.speed",), riskLevel="LOW"),
            Tool(name="spotify.setVolume", description="Set playback volume.", parameters={"volume": {"type": "integer"}}, module="spotify", method="setVolume", safe=True, offlineAllowed=True, requiredPermissions=("spotify.volume",), riskLevel="LOW"),
            Tool(name="spotify.searchTracks", description="Search tracks.", parameters={"query": {"type": "string"}}, module="spotify", method="searchTracks", safe=True, offlineAllowed=True, requiredPermissions=("spotify.search",), riskLevel="LOW"),
            Tool(name="spotify.searchPlaylists", description="Search playlists.", parameters={"query": {"type": "string"}}, module="spotify", method="searchPlaylists", safe=True, offlineAllowed=True, requiredPermissions=("spotify.search",), riskLevel="LOW"),
            Tool(name="spotify.playPlaylist", description="Play a playlist.", parameters={"playlistId": {"type": "string"}, "query": {"type": "string"}, "shuffle": {"type": "boolean"}}, module="spotify", method="playPlaylist", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playlists", "spotify.playback"), riskLevel="LOW"),
            Tool(name="spotify.getNowPlaying", description="Get the current now-playing payload.", parameters={}, module="spotify", method="getNowPlaying", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playback",), riskLevel="LOW"),
            Tool(name="spotify.getPlaybackState", description="Get the current playback state snapshot.", parameters={}, module="spotify", method="getPlaybackState", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playback",), riskLevel="LOW"),
            Tool(name="spotify.listDevices", description="List Spotify devices.", parameters={}, module="spotify", method="listDevices", safe=True, offlineAllowed=True, requiredPermissions=("spotify.devices",), riskLevel="LOW"),
            Tool(name="spotify.transferPlayback", description="Transfer playback to a different device.", parameters={"deviceId": {"type": "string"}}, module="spotify", method="transferPlayback", safe=False, offlineAllowed=True, confirmRequired=True, requiredPermissions=("spotify.devices",), riskLevel="MODERATE"),
            Tool(name="spotify.listPlaylists", description="List saved playlists.", parameters={}, module="spotify", method="listPlaylists", safe=True, offlineAllowed=True, requiredPermissions=("spotify.playlists",), riskLevel="LOW"),
        ]

    def _standaloneIntent(self, intentName: str, data: dict[str, object]):
        if intentName in {"spotify.play", "spotify.playTrack"}:
            return self._fallbackPlayback(str(data.get("track") or data.get("query") or "Track"), artist=str(data.get("artist") or ""), playlist=str(data.get("playlist") or ""), isPlaying=True)
        if intentName == "spotify.pause":
            return self._fallbackPlayback("Track", isPlaying=False)
        if intentName == "spotify.next":
            return self._fallbackPlayback("Next track", isPlaying=True)
        if intentName == "spotify.previous":
            return self._fallbackPlayback("Previous track", isPlaying=True)
        if intentName in {"spotify.search", "spotify.searchTracks"}:
            return self._fallbackSearch(str(data.get("query") or data.get("track") or ""), "tracks")
        if intentName == "spotify.searchPlaylists":
            return self._fallbackSearch(str(data.get("query") or ""), "playlists")
        if intentName == "spotify.playPlaylist":
            return self._fallbackPlayback(str(data.get("query") or data.get("playlist") or "Playlist"), playlist=str(data.get("query") or data.get("playlist") or ""), isPlaying=True)
        if intentName == "spotify.seek":
            return {"positionMs": self._coerceInt(data.get("positionMs")), "offsetMs": self._coerceInt(data.get("offsetMs"))}
        if intentName == "spotify.speed":
            return {"playbackSpeed": float(data.get("speed") or 1.0)}
        if intentName == "spotify.volume":
            return {"volume": int(data.get("volume") or 0)}
        if intentName == "spotify.nowPlaying":
            return self._fallbackPlayback("Track", isPlaying=False)
        if intentName == "spotify.listDevices":
            return self.listDevices()
        if intentName == "spotify.transferDevice":
            return {"deviceId": str(data.get("deviceId") or data.get("device") or "")}
        if intentName == "spotify.listPlaylists":
            return self.listPlaylists()
        raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")

    @staticmethod
    def _coerceInt(value):
        try:
            return int(value) if value is not None and str(value) != "" else None
        except Exception:
            return None

    @staticmethod
    def _fallbackPlayback(track: str, artist: str = "", playlist: str = "", isPlaying: bool = False):
        currentTrack = f"{artist} - {track}".strip(" -") if artist else str(track or "Unknown track")
        return {
            "track": str(track or ""),
            "artist": str(artist or ""),
            "currentTrack": currentTrack,
            "album": "",
            "duration": 180000,
            "progress": 0,
            "isPlaying": bool(isPlaying),
            "volume": 100,
            "playbackSpeed": 1.0,
            "shuffleEnabled": False,
            "repeatMode": "off",
            "activeDevice": "Desktop",
            "playlist": str(playlist or ""),
            "timestamp": _utcNow(),
            "source": "mock",
            "metadata": {},
        }

    @staticmethod
    def _fallbackSearch(query: str, kind: str):
        lowered = str(query or "").strip()
        if kind == "playlists":
            return {"query": lowered, "playlists": [{"playlistId": "playlist-coding", "name": "Coding Mix", "description": "Focus music for deep work."}], "tracks": [], "artists": [], "albums": [], "source": "mock", "timestamp": _utcNow(), "metadata": {}}
        if kind == "artists":
            return {"query": lowered, "artists": [{"artistId": "artist-aura", "name": "Aura"}], "tracks": [], "playlists": [], "albums": [], "source": "mock", "timestamp": _utcNow(), "metadata": {}}
        if kind == "albums":
            return {"query": lowered, "albums": [{"albumId": "album-focus", "name": "Focus Flow"}], "tracks": [], "playlists": [], "artists": [], "source": "mock", "timestamp": _utcNow(), "metadata": {}}
        return {"query": lowered, "tracks": [{"trackId": "track-coding-mix-1", "title": lowered or "Coding Dreams", "artist": "Aura", "album": "Coding Mix"}], "playlists": [], "artists": [], "albums": [], "source": "mock", "timestamp": _utcNow(), "metadata": {}}
