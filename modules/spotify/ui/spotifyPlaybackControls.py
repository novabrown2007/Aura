"""Playback controls payload for the desktop overlay."""

from __future__ import annotations


class SpotifyPlaybackControls:
    """Describe the interactive controls Aura can expose."""

    def __init__(self, playbackState=None):
        self.playbackState = playbackState or {}

    def render(self):
        payload = self._payload()
        return {
            "canPlay": True,
            "canPause": True,
            "canSeek": True,
            "canAdjustVolume": True,
            "canAdjustSpeed": True,
            "isPlaying": bool(payload.get("isPlaying")),
            "volume": int(payload.get("volume") or 0),
            "playbackSpeed": float(payload.get("playbackSpeed") or 1.0),
        }

    def _payload(self):
        if hasattr(self.playbackState, "asDict"):
            return self.playbackState.asDict()
        return dict(self.playbackState or {})
