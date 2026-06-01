"""Spotify module permission definitions."""

from core.modules.modulePermissions import ModulePermissions

SPOTIFY_PERMISSIONS = ModulePermissions(
    capabilityPermissions=(
        "spotify.playback",
        "spotify.search",
        "spotify.playlists",
        "spotify.devices",
        "spotify.queue",
        "spotify.seek",
        "spotify.volume",
        "spotify.speed",
        "spotify.control",
    ),
    externalApiPermissions=("network:https",),
    deviceAccessPermissions=("media.playback",),
)
