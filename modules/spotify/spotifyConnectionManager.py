"""Spotify connection lifecycle manager."""

from __future__ import annotations

from modules.spotify.providers import SpotifyApiProvider


class SpotifyConnectionManager:
    """Coordinate Spotify session state and token refresh."""

    def __init__(self, context=None, provider: SpotifyApiProvider | None = None):
        self.context = context
        self.provider = provider or SpotifyApiProvider(context)
        self.lastConnectionState = self.provider.getConnectionState()

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self.provider.initialize(self.context)
        self.lastConnectionState = self.provider.connect()
        self._emit("spotify.connected", self.lastConnectionState.asDict())
        self._notify("Spotify connected", "Spotify playback is available.", "LOW")
        return self.lastConnectionState

    def connect(self):
        self.lastConnectionState = self.provider.connect()
        self._emit("spotify.connected", self.lastConnectionState.asDict())
        self._notify("Spotify connected", "Spotify playback is available.", "LOW")
        return self.lastConnectionState

    def disconnect(self, reason: str = ""):
        self.lastConnectionState = self.provider.disconnect(reason)
        self._emit("spotify.disconnected", {"reason": reason, **self.lastConnectionState.asDict()})
        self._notify("Spotify disconnected", reason or "Spotify playback disconnected.", "NORMAL")
        return self.lastConnectionState

    def refreshToken(self):
        self.lastConnectionState = self.provider.refreshToken()
        return self.lastConnectionState

    def getState(self):
        return self.provider.getConnectionState()

    def ensureConnected(self):
        if not self.provider.isAvailable():
            return self.connect()
        return self.getState()

    def shutdown(self):
        self.disconnect("shutdown")

    def _emit(self, eventName: str, payload: dict[str, object]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        return eventBus.emit(eventName, payload or {})

    def _notify(self, title: str, message: str, priority: str):
        notificationManager = getattr(self.context, "notificationManager", None)
        if notificationManager is None or not hasattr(notificationManager, "createNotification"):
            return None
        try:
            return notificationManager.createNotification(
                {
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "category": "MEDIA",
                    "source": "spotify",
                },
                eventName="spotify.notification",
            )
        except Exception:
            return None
