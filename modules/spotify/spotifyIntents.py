"""Spotify module intent definitions."""

from core.modules.base.moduleIntent import ModuleIntent

SPOTIFY_INTENTS = (
    ModuleIntent(
        name="spotify.play",
        description="Start music playback.",
        arguments={"track": {"type": "string"}, "artist": {"type": "string"}},
        target="playSong",
    ),
    ModuleIntent(
        name="spotify.pause",
        description="Pause music playback.",
        target="pauseMusic",
    ),
    ModuleIntent(
        name="spotify.search",
        description="Search for music.",
        arguments={"query": {"type": "string"}},
        target="searchTracks",
        requiredArguments=("query",),
    ),
)
