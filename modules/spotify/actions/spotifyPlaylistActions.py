"""Spotify playlist-specific actions."""

from core.modules.base.moduleAction import ModuleAction


SPOTIFY_PLAYLIST_ACTIONS = (
    ModuleAction(
        name="spotify.searchTracks",
        description="Search for tracks.",
        method="searchTracks",
        parameters={"query": {"type": "string"}},
        permissions=("spotify.search",),
        capabilities=("spotify.search",),
        target="searchTracks",
    ),
    ModuleAction(
        name="spotify.searchPlaylists",
        description="Search for playlists.",
        method="searchPlaylists",
        parameters={"query": {"type": "string"}},
        permissions=("spotify.search",),
        capabilities=("spotify.search",),
        target="searchPlaylists",
    ),
    ModuleAction(
        name="spotify.playPlaylist",
        description="Play a playlist by name or identifier.",
        method="playPlaylist",
        parameters={"playlistId": {"type": "string"}, "query": {"type": "string"}},
        permissions=("spotify.playlists", "spotify.playback"),
        capabilities=("spotify.playlists", "spotify.playback"),
        target="playPlaylist",
    ),
    ModuleAction(
        name="spotify.listPlaylists",
        description="List saved playlists.",
        method="listPlaylists",
        permissions=("spotify.playlists",),
        capabilities=("spotify.playlists",),
        target="listPlaylists",
    ),
)
