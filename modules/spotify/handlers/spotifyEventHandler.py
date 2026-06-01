"""Spotify event handler for runtime integration."""

from __future__ import annotations


class SpotifyEventHandler:
    """Bridge Spotify module events into runtime coordination."""

    def __init__(self, manager=None):
        self.manager = manager

    def handleEvent(self, event):
        if self.manager is None:
            return None
        return self.manager.handleEvent(event)
