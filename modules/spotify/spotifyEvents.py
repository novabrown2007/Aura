"""Spotify module event names."""


class SpotifyEvents:
    """Spotify runtime event constants."""

    CONNECTED = "spotify.connected"
    DISCONNECTED = "spotify.disconnected"
    TRACK_CHANGED = "spotify.track.changed"
    PLAYBACK_STARTED = "spotify.playback.started"
    PLAYBACK_PAUSED = "spotify.playback.paused"
    PLAYLIST_CHANGED = "spotify.playlist.changed"
    DEVICE_CHANGED = "spotify.device.changed"
    SEARCHED = "spotify.search.performed"
    REQUESTED = "spotify.requested"
