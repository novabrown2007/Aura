"""Tests for the Aura media manager page."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from interface.pages.media_manager_page import MediaManagerPage


class DummyCanvas:
    """Minimal canvas stub for page rendering tests."""

    def __init__(self):
        self._next_id = 1

    def _alloc(self):
        item_id = self._next_id
        self._next_id += 1
        return item_id

    def create_text(self, *args, **kwargs):
        return self._alloc()

    def create_line(self, *args, **kwargs):
        return self._alloc()

    def create_rectangle(self, *args, **kwargs):
        return self._alloc()

    def create_polygon(self, *args, **kwargs):
        return self._alloc()

    def create_oval(self, *args, **kwargs):
        return self._alloc()

    def create_image(self, *args, **kwargs):
        return self._alloc()

    def tag_bind(self, *args, **kwargs):
        return None

    def tag_raise(self, *args, **kwargs):
        return None


class FakeSpotify:
    """Deterministic Spotify stand-in for media page tests."""

    def __init__(self):
        self.calls = []
        self.state = {
            "track": "Orbit",
            "artist": "Aura",
            "album": "Night Drive",
            "duration": 240000,
            "progress": 60000,
            "isPlaying": True,
            "volume": 42,
            "activeDevice": "Desktop",
            "source": "mock",
        }

    def getPlaybackState(self):
        self.calls.append(("getPlaybackState",))
        return dict(self.state)

    def getNowPlaying(self):
        self.calls.append(("getNowPlaying",))
        return dict(self.state)

    def listPlaylists(self):
        self.calls.append(("listPlaylists",))
        return [{"playlistId": "playlist-1", "name": "Coding Mix", "description": "Focus"}]

    def searchTracks(self, query):
        self.calls.append(("searchTracks", query))
        return {"tracks": [{"trackId": f"track-{query}", "title": f"{query} Song", "artist": "Aura"}]}

    def searchPlaylists(self, query):
        self.calls.append(("searchPlaylists", query))
        return {"playlists": [{"playlistId": f"playlist-{query}", "name": f"{query} Mix", "description": "Browse"}]}

    def playTrack(self, **kwargs):
        self.calls.append(("playTrack", kwargs))
        return kwargs

    def playPlaylist(self, **kwargs):
        self.calls.append(("playPlaylist", kwargs))
        return kwargs

    def previousTrack(self):
        self.calls.append(("previousTrack",))
        return dict(self.state)

    def nextTrack(self):
        self.calls.append(("nextTrack",))
        return dict(self.state)

    def pauseMusic(self):
        self.calls.append(("pauseMusic",))
        self.state["isPlaying"] = False
        return dict(self.state)

    def resumeMusic(self):
        self.calls.append(("resumeMusic",))
        self.state["isPlaying"] = True
        return dict(self.state)

    def setVolume(self, volume):
        self.calls.append(("setVolume", volume))
        self.state["volume"] = int(volume)
        return dict(self.state)


class MediaManagerPageTests(unittest.TestCase):
    """Media page behavior testing.tests."""

    def test_search_and_selection(self):
        spotify = FakeSpotify()
        page = MediaManagerPage(context=SimpleNamespace(spotify=spotify))
        canvas = DummyCanvas()

        page.render(canvas, 1200, 800, SimpleNamespace(
            text="#fff",
            placeholder="#999",
            tertiary_background="#222",
            border="#444",
            shadow="#111",
            secondary_accent="#0af",
            panel="#333",
            background="#000",
            soft_glow="#0af",
        ), sidebar_visible=False)

        self.assertIn(("getPlaybackState",), spotify.calls)
        self.assertIn(("listPlaylists",), spotify.calls)
        self.assertFalse(page._track_results)
        self.assertFalse(page._playlist_results)

        self.assertTrue(page.handle_press(page._search_bounds[0] + 4, page._search_bounds[1] + 4, 1200, 800, False))
        for char in "lofi":
            self.assertTrue(page.handle_keypress(SimpleNamespace(keysym=char, char=char)))
        self.assertTrue(page.handle_keypress(SimpleNamespace(keysym="Return", char="\r")))

        self.assertIn(("searchTracks", "lofi"), spotify.calls)
        self.assertIn(("searchPlaylists", "lofi"), spotify.calls)

        page.render(canvas, 1200, 800, SimpleNamespace(
            text="#fff",
            placeholder="#999",
            tertiary_background="#222",
            border="#444",
            shadow="#111",
            secondary_accent="#0af",
            panel="#333",
            background="#000",
            soft_glow="#0af",
        ), sidebar_visible=False)

        self.assertTrue(page._track_hitboxes)
        self.assertTrue(page._playlist_hitboxes)

        bounds, _item = page._playlist_hitboxes[0]
        click_x = bounds[0] + 4
        click_y = bounds[1] + 4
        self.assertTrue(page.handle_press(click_x, click_y, 1200, 800, False))
        self.assertTrue(any(call[0] == "playPlaylist" for call in spotify.calls))


if __name__ == "__main__":
    unittest.main()
