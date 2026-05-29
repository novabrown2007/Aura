"""Mock Spotify capability module for Aura."""

from __future__ import annotations

from core.modules.base.auraModule import AuraModule
from core.modules.base.moduleMetadata import ModuleMetadata
from modules.spotify.spotifyActions import SPOTIFY_ACTIONS
from modules.spotify.spotifyEvents import SpotifyEvents
from modules.spotify.spotifyIntents import SPOTIFY_INTENTS
from modules.spotify.spotifyPermissions import SPOTIFY_PERMISSIONS


class SpotifyModule(AuraModule):
    """Deterministic Spotify capability placeholder."""

    metadata = ModuleMetadata(
        name="spotify",
        version="1.0.0",
        author="Aura",
        description="Local Spotify capability placeholder.",
        permissions=tuple(SPOTIFY_PERMISSIONS.asList()),
        capabilities=("music.playback", "music.search"),
    )

    def __init__(self, context=None):
        super().__init__()
        self.currentTrack = ""
        self.isPlaying = False
        self.lastQuery = ""
        self._lastHandledEvent = ""
        if context is not None:
            self.initialize(context)

    def initialize(self, context):
        super().initialize(context)
        self.currentTrack = ""
        self.isPlaying = False
        self.lastQuery = ""
        if self.logger:
            self.logger.info("spotify module started.")

    def getIntents(self):
        return list(SPOTIFY_INTENTS)

    def getActions(self):
        return list(SPOTIFY_ACTIONS)

    def getPermissions(self):
        return SPOTIFY_PERMISSIONS

    def getSubscriptions(self):
        return ["conversation.started"]

    def handleEvent(self, event):
        self._lastHandledEvent = getattr(event, "name", "")
        return None

    def playSong(self, track: str = "", artist: str = "") -> dict[str, object]:
        """Start deterministic mock playback."""

        self.currentTrack = " - ".join(part for part in (artist, track) if part).strip(" -")
        self.isPlaying = True
        payload = {
            "track": str(track or ""),
            "artist": str(artist or ""),
            "currentTrack": self.currentTrack or "Unknown track",
            "isPlaying": True,
        }
        self.emit(SpotifyEvents.REQUESTED, payload)
        self.emit(SpotifyEvents.PLAYBACK_CHANGED, payload)
        return payload

    def pauseMusic(self) -> dict[str, object]:
        """Pause deterministic mock playback."""

        self.isPlaying = False
        payload = {"currentTrack": self.currentTrack or "Unknown track", "isPlaying": False}
        self.emit(SpotifyEvents.PLAYBACK_CHANGED, payload)
        return payload

    def searchTracks(self, query: str) -> dict[str, object]:
        """Return a deterministic mock search response."""

        self.lastQuery = str(query or "")
        results = [
            {"title": f"{self.lastQuery} Radio", "artist": "Aura"},
            {"title": f"{self.lastQuery} Mix", "artist": "Aura"},
        ] if self.lastQuery else []
        payload = {"query": self.lastQuery, "results": results}
        self.emit(SpotifyEvents.SEARCHED, payload)
        return payload

    def handleIntent(self, intent):
        """Handle Spotify intents through the placeholder actions."""

        intentName = getattr(intent, "name", intent)
        arguments = getattr(intent, "arguments", {}) or {}
        if intentName == "spotify.play":
            return self.playSong(arguments.get("track", ""), arguments.get("artist", ""))
        if intentName == "spotify.pause":
            return self.pauseMusic()
        if intentName == "spotify.search":
            return self.searchTracks(arguments.get("query", ""))
        raise NotImplementedError(f"{self.metadata.name} does not handle intent {intentName}.")
