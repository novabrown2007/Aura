"""Spotify module intent definitions."""

from core.modules.base.moduleIntent import ModuleIntent


SPOTIFY_INTENTS = (
    ModuleIntent(name="spotify.play", description="Play a track or playlist.", target="playTrack", arguments={"query": "string"}),
    ModuleIntent(name="spotify.pause", description="Pause Spotify playback.", target="pausePlayback"),
    ModuleIntent(name="spotify.next", description="Skip to the next track.", target="nextTrack"),
    ModuleIntent(name="spotify.previous", description="Return to the previous track.", target="previousTrack"),
    ModuleIntent(name="spotify.search", description="Search music, artists, albums, or playlists.", target="searchTracks", arguments={"query": "string"}),
    ModuleIntent(name="spotify.playPlaylist", description="Start playback from a playlist.", target="playPlaylist", arguments={"query": "string"}),
    ModuleIntent(name="spotify.seek", description="Seek within the current track.", target="seekPlayback", arguments={"offsetMs": "integer"}),
    ModuleIntent(name="spotify.speed", description="Adjust playback speed.", target="setPlaybackSpeed", arguments={"speed": "number"}),
    ModuleIntent(name="spotify.volume", description="Adjust playback volume.", target="setVolume", arguments={"volume": "integer"}),
    ModuleIntent(name="spotify.nowPlaying", description="Report current playback state.", target="getNowPlaying"),
    ModuleIntent(name="spotify.listDevices", description="List available Spotify devices.", target="listDevices"),
    ModuleIntent(name="spotify.transferDevice", description="Transfer playback to another device.", target="transferPlayback", arguments={"deviceId": "string"}),
    ModuleIntent(name="spotify.listPlaylists", description="List saved playlists.", target="listPlaylists"),
)
