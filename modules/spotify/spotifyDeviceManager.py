"""Spotify device management."""

from __future__ import annotations

from modules.spotify.events import SpotifyEvents


class SpotifyDeviceManager:
    """Expose active playback devices and device transfer support."""

    def __init__(self, context=None, provider=None):
        self.context = context
        self.provider = provider

    def initialize(self, context=None, provider=None):
        if context is not None:
            self.context = context
        if provider is not None:
            self.provider = provider
        return self

    def listDevices(self):
        return list(self.provider.listDevices())

    def getActiveDevice(self):
        devices = self.listDevices()
        return next((device for device in devices if device.get("isActive")), devices[0] if devices else None)

    def transferPlayback(self, deviceId: str):
        state = self.provider.transferPlayback(deviceId)
        self._emit(SpotifyEvents.DEVICE_CHANGED, {"deviceId": deviceId, "activeDevice": state.activeDevice})
        return state.asDict()

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})
