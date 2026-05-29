"""Spotify capability module for Aura."""

from modules.spotify.spotifyActions import SPOTIFY_ACTIONS
from modules.spotify.spotifyEvents import SpotifyEvents
from modules.spotify.spotifyIntents import SPOTIFY_INTENTS
from modules.spotify.spotifyModule import SpotifyModule
from modules.spotify.spotifyPermissions import SPOTIFY_PERMISSIONS

MODULE_METADATA = SpotifyModule.metadata


def createModule(context=None):
    """Create the Spotify Aura module."""

    return SpotifyModule()


def register(context):
    """Register the Spotify module with the runtime context."""

    context.spotify = SpotifyModule(context)


__all__ = [
    "MODULE_METADATA",
    "SpotifyEvents",
    "SPOTIFY_ACTIONS",
    "SPOTIFY_INTENTS",
    "SPOTIFY_PERMISSIONS",
    "SpotifyModule",
    "createModule",
    "register",
]
