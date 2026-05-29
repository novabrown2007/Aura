"""Spotify module permission definitions."""

from core.modules.modulePermissions import ModulePermissions

SPOTIFY_PERMISSIONS = ModulePermissions(
    capabilityPermissions=("music.playback", "music.search"),
    externalApiPermissions=("network:http",),
)
