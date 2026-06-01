"""Spotify action dispatcher."""

from __future__ import annotations


class SpotifyActionExecutor:
    """Map named actions to the manager surface."""

    def __init__(self, manager=None):
        self.manager = manager

    def initialize(self, manager=None):
        if manager is not None:
            self.manager = manager
        return self

    def execute(self, actionName: str, arguments: dict[str, object] | None = None):
        arguments = dict(arguments or {})
        actionName = str(actionName or "")
        if actionName == "spotify.playTrack":
            return self.manager.playTrack(**arguments)
        if actionName == "spotify.pause":
            return self.manager.pauseMusic()
        if actionName == "spotify.nextTrack":
            return self.manager.nextTrack()
        if actionName == "spotify.previousTrack":
            return self.manager.previousTrack()
        if actionName == "spotify.seek":
            return self.manager.seekPlayback(**arguments)
        if actionName == "spotify.setPlaybackSpeed":
            return self.manager.setPlaybackSpeed(**arguments)
        if actionName == "spotify.setVolume":
            return self.manager.setVolume(**arguments)
        if actionName == "spotify.transferPlayback":
            return self.manager.transferPlayback(**arguments)
        if actionName == "spotify.playPlaylist":
            return self.manager.playPlaylist(**arguments)
        if actionName == "spotify.searchTracks":
            return self.manager.searchTracks(**arguments)
        if actionName == "spotify.searchPlaylists":
            return self.manager.searchPlaylists(**arguments)
        if actionName == "spotify.listPlaylists":
            return self.manager.listPlaylists()
        if actionName == "spotify.listDevices":
            return self.manager.listDevices()
        if actionName == "spotify.getNowPlaying":
            return self.manager.getNowPlaying()
        if actionName == "spotify.getPlaybackState":
            return self.manager.getPlaybackState()
        raise KeyError(f"Unknown Spotify action: {actionName}")
