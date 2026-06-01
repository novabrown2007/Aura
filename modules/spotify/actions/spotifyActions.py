"""Spotify module action definitions."""

from core.modules.base.moduleAction import ModuleAction


SPOTIFY_ACTIONS = (
    ModuleAction(
        name="spotify.playTrack",
        description="Play a track by name or identifier.",
        method="playTrack",
        parameters={"trackId": {"type": "string"}, "query": {"type": "string"}},
        permissions=("spotify.playback",),
        capabilities=("spotify.playback",),
        target="playTrack",
    ),
    ModuleAction(
        name="spotify.pause",
        description="Pause Spotify playback.",
        method="pausePlayback",
        permissions=("spotify.playback",),
        capabilities=("spotify.playback",),
        target="pausePlayback",
    ),
    ModuleAction(
        name="spotify.nextTrack",
        description="Skip to the next track.",
        method="nextTrack",
        permissions=("spotify.playback",),
        capabilities=("spotify.playback",),
        target="nextTrack",
    ),
    ModuleAction(
        name="spotify.previousTrack",
        description="Return to the previous track.",
        method="previousTrack",
        permissions=("spotify.playback",),
        capabilities=("spotify.playback",),
        target="previousTrack",
    ),
    ModuleAction(
        name="spotify.seek",
        description="Seek playback to a position or offset.",
        method="seekPlayback",
        parameters={"positionMs": {"type": "integer"}, "offsetMs": {"type": "integer"}},
        permissions=("spotify.seek",),
        capabilities=("spotify.seek",),
        target="seekPlayback",
    ),
    ModuleAction(
        name="spotify.setPlaybackSpeed",
        description="Change playback speed.",
        method="setPlaybackSpeed",
        parameters={"speed": {"type": "number"}},
        permissions=("spotify.speed",),
        capabilities=("spotify.speed",),
        target="setPlaybackSpeed",
    ),
    ModuleAction(
        name="spotify.setVolume",
        description="Adjust playback volume.",
        method="setVolume",
        parameters={"volume": {"type": "integer"}},
        permissions=("spotify.volume",),
        capabilities=("spotify.volume",),
        target="setVolume",
    ),
    ModuleAction(
        name="spotify.transferPlayback",
        description="Transfer playback to another device.",
        method="transferPlayback",
        parameters={"deviceId": {"type": "string"}},
        permissions=("spotify.devices",),
        capabilities=("spotify.devices",),
        target="transferPlayback",
    ),
)
