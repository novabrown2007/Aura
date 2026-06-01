"""Now playing view model for the desktop overlay."""

from __future__ import annotations


class SpotifyNowPlayingView:
    """Render the current media state into a compact overlay payload."""

    def __init__(self, playbackState=None):
        self.playbackState = playbackState or {}

    def render(self):
        playback = self._payload()
        return {
            "title": playback.get("track") or "Nothing playing",
            "artist": playback.get("artist") or "",
            "album": playback.get("album") or "",
            "isPlaying": bool(playback.get("isPlaying")),
            "progress": int(playback.get("progress") or 0),
            "duration": int(playback.get("duration") or 0),
            "device": playback.get("activeDevice") or "",
            "source": playback.get("source") or "mock",
        }

    def _payload(self):
        if hasattr(self.playbackState, "asDict"):
            return self.playbackState.asDict()
        return dict(self.playbackState or {})
