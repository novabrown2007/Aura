"""Spotify playback-specific actions."""

from core.modules.base.moduleAction import ModuleAction


SPOTIFY_PLAYBACK_ACTIONS = (
    ModuleAction(
        name="spotify.getNowPlaying",
        description="Get the current playback state.",
        method="getNowPlaying",
        permissions=("spotify.playback",),
        capabilities=("spotify.playback",),
        target="getNowPlaying",
    ),
    ModuleAction(
        name="spotify.getPlaybackState",
        description="Get a detailed playback snapshot.",
        method="getPlaybackState",
        permissions=("spotify.playback",),
        capabilities=("spotify.playback",),
        target="getPlaybackState",
    ),
)
