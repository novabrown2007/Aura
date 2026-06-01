"""Spotify device monitor."""

from __future__ import annotations

from modules.spotify.events import SpotifyEvents


class SpotifyDeviceMonitor:
    """Detect device changes and keep the assistant state fresh."""

    def __init__(self, context=None, provider=None):
        self.context = context
        self.provider = provider
        self._lastDevices = []

    def initialize(self, context=None, provider=None):
        if context is not None:
            self.context = context
        if provider is not None:
            self.provider = provider
        self._lastDevices = self.listDevices()
        return self

    def poll(self):
        devices = self.listDevices()
        if devices != self._lastDevices:
            self._emit(SpotifyEvents.DEVICE_CHANGED, {"devices": devices})
            self._lastDevices = devices
        return devices

    def listDevices(self):
        return list(self.provider.listDevices()) if self.provider is not None else []

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})
