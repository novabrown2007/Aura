"""Spotify module action definitions."""

from core.modules.base.moduleAction import ModuleAction

SPOTIFY_ACTIONS = (
    ModuleAction(
        name="spotify.play",
        description="Play a track or playlist.",
        method="playSong",
        parameters={"track": {"type": "string"}, "artist": {"type": "string"}},
        capabilities=("music.playback",),
    ),
    ModuleAction(
        name="spotify.pause",
        description="Pause playback.",
        method="pauseMusic",
        capabilities=("music.playback",),
    ),
    ModuleAction(
        name="spotify.search",
        description="Search for tracks.",
        method="searchTracks",
        parameters={"query": {"type": "string"}},
        requiredParameters=("query",),
        capabilities=("music.search",),
    ),
)
