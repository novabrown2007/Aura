"""Spotify capability module for Aura."""

from modules.spotify.actions import SPOTIFY_ACTIONS, SPOTIFY_PLAYBACK_ACTIONS, SPOTIFY_PLAYLIST_ACTIONS
from modules.spotify.events import SpotifyEvents
from modules.spotify.intents import SPOTIFY_INTENTS
from modules.spotify.spotifyManager import SpotifyManager
from modules.spotify.spotifyModule import SpotifyModule
from modules.spotify.spotifyPermissions import SPOTIFY_PERMISSIONS

MODULE_METADATA = SpotifyModule.metadata


def createModule(context=None):
    """Create the Spotify Aura module."""

    return SpotifyModule(context)


def register(context):
    """Register the Spotify module with the runtime context."""

    context.spotify = SpotifyModule(context)


__all__ = [
    "MODULE_METADATA",
    "SpotifyEvents",
    "SPOTIFY_ACTIONS",
    "SPOTIFY_PLAYBACK_ACTIONS",
    "SPOTIFY_PLAYLIST_ACTIONS",
    "SPOTIFY_INTENTS",
    "SPOTIFY_PERMISSIONS",
    "SpotifyManager",
    "SpotifyModule",
    "createModule",
    "register",
]
