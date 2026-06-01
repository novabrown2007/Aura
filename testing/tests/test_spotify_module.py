"""Tests for Aura's unified Spotify media module."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from core.router.intent import Intent
from modules.spotify import SpotifyModule
from modules.spotify.providers import SpotifyApiProvider
from testing.tests.support.fakes import make_context


class FakeEventBus:
    """Lightweight event bus that records every emission."""

    def __init__(self):
        self.events = []
        self.listeners = {}

    def emit(self, event, data=None):
        if isinstance(event, str):
            payload = {"name": event, "data": dict(data or {})}
        else:
            payload = {"name": getattr(event, "name", ""), "data": dict(getattr(event, "data", {}) or {})}
        self.events.append(payload)
        for callback in self.listeners.get(payload["name"], []):
            callback(payload)
        return payload

    def subscribe(self, event_name, callback):
        self.listeners.setdefault(event_name, []).append(callback)


class FakeNotificationManager:
    """Capture Spotify notifications without invoking the full UI stack."""

    def __init__(self):
        self.created = []

    def createNotification(self, payload, eventName=""):
        record = {"payload": dict(payload), "eventName": eventName}
        self.created.append(record)
        return record


class SpotifyModuleTests(unittest.TestCase):
    """Validate the Spotify connection and controller module."""

    def setUp(self):
        self.context = make_context()
        self.context.config._data["spotify"] = {
            "spotifyEnabled": True,
            "spotifyPlaybackMonitoringEnabled": True,
            "spotifyOverlayEnabled": True,
            "spotifyCacheEnabled": True,
            "spotifyReconnectEnabled": True,
            "spotifyPollingIntervalSeconds": 2,
            "defaultDevice": "Desktop",
            "cachePath": "temp/spotify_test_cache.sqlite3",
        }
        self.context.eventManager = FakeEventBus()
        self.context.notificationManager = FakeNotificationManager()

    def test_module_exposes_standard_spotify_contract(self):
        module = SpotifyModule()
        toolNames = {tool.name for tool in module.getTools()}

        self.assertEqual(module.metadata.name, "spotify")
        self.assertIn("spotify.playback", module.metadata.capabilities)
        self.assertEqual(len(module.getIntents()), 13)
        self.assertGreaterEqual(len(module.getActions()), 1)
        self.assertIn("spotify.playTrack", toolNames)
        self.assertIn("spotify.pause", toolNames)
        self.assertIn("spotify.nextTrack", toolNames)
        self.assertIn("spotify.previousTrack", toolNames)
        self.assertIn("spotify.seek", toolNames)
        self.assertIn("spotify.setPlaybackSpeed", toolNames)
        self.assertIn("spotify.setVolume", toolNames)
        self.assertIn("spotify.searchTracks", toolNames)
        self.assertIn("spotify.searchPlaylists", toolNames)
        self.assertIn("spotify.playPlaylist", toolNames)
        self.assertIn("spotify.getNowPlaying", toolNames)
        self.assertIn("spotify.getPlaybackState", toolNames)
        self.assertIn("spotify.listDevices", toolNames)
        self.assertIn("spotify.transferPlayback", toolNames)
        self.assertIn("spotify.listPlaylists", toolNames)

    def test_connection_refresh_and_state_tracking(self):
        module = self._makeModule()
        connection = module.manager.getConnectionState()
        refreshed = module.manager.connectionManager.refreshToken()

        self.assertEqual(connection["status"], "CONNECTED")
        self.assertEqual(refreshed.status, "CONNECTED")
        self.assertTrue(refreshed.expiresAt)

    def test_playback_controls_seek_and_speed(self):
        module = self._makeModule()

        played = module.playSong(track="Example", artist="Artist")
        paused = module.pauseMusic()
        seeked = module.seekPlayback(offsetMs=30000)
        speed = module.setPlaybackSpeed(1.5)
        volume = module.setVolume(65)

        self.assertTrue(played["isPlaying"])
        self.assertEqual(played["currentTrack"], "Artist - Example")
        self.assertFalse(paused["isPlaying"])
        self.assertEqual(seeked["progress"], 30000)
        self.assertEqual(speed["playbackSpeed"], 1.5)
        self.assertEqual(volume["volume"], 65)

    def test_playlist_selection_and_now_playing(self):
        module = self._makeModule()

        result = module.playPlaylist(query="coding")
        nowPlaying = module.getNowPlaying()

        self.assertTrue(result["isPlaying"])
        self.assertEqual(result["playlist"], "Coding Mix")
        self.assertEqual(nowPlaying["playlist"], "Coding Mix")
        self.assertIn("currentTrack", nowPlaying)

    def test_search_and_devices(self):
        module = self._makeModule()

        tracks = module.searchTracks("focus")
        devices = module.listDevices()
        transferred = module.transferPlayback("device-phone")

        self.assertGreaterEqual(len(tracks["tracks"]), 1)
        self.assertEqual(devices[0]["name"], "Desktop")
        self.assertEqual(transferred["activeDevice"], "Phone")
        self.assertGreaterEqual(len(self.context.notificationManager.created), 1)

    def test_playback_monitoring_emits_events(self):
        module = self._makeModule()
        self.context.eventManager.events.clear()

        module.playSong(track="Example", artist="Artist")
        module.manager.playbackMonitor.poll()

        eventNames = [event["name"] for event in self.context.eventManager.events]
        self.assertIn("spotify.playback.started", eventNames)
        self.assertIn("spotify.track.changed", eventNames)

    def test_ui_views_render_compact_payloads(self):
        module = self._makeModule()
        module.playPlaylist(query="coding")

        nowPlaying = module.getNowPlayingView()
        controls = module.getPlaybackControls()
        playlistView = module.getPlaylistView()
        overlay = module.getOverlayWidget()

        self.assertIn("title", nowPlaying)
        self.assertIn("isPlaying", controls)
        self.assertGreaterEqual(playlistView["count"], 1)
        self.assertTrue(overlay["compact"])

    def test_handle_intent_returns_structured_response(self):
        module = self._makeModule()

        response = module.handleIntent(Intent("spotify.playPlaylist", "Play my coding playlist", {"query": "coding"}))

        self.assertIn("spokenText", response)
        self.assertIn("uiText", response)
        self.assertIn("actions", response)
        self.assertIn("metadata", response)

    def test_standalone_fallback_still_preserves_legacy_fields(self):
        module = SpotifyModule()

        played = module.playSong(track="Example", artist="Artist")
        paused = module.pauseMusic()

        self.assertTrue(played["isPlaying"])
        self.assertEqual(played["currentTrack"], "Artist - Example")
        self.assertFalse(paused["isPlaying"])

    def test_api_provider_connection_and_search(self):
        provider = SpotifyApiProvider(self.context)
        provider.initialize(self.context)

        connection = provider.getConnectionState()
        search = provider.searchPlaylists("coding")

        self.assertTrue(connection.isConnected())
        self.assertGreaterEqual(len(search.playlists), 1)

    def _makeModule(self):
        return SpotifyModule(self.context)


if __name__ == "__main__":
    unittest.main()
