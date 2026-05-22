"""Normalized bridge state cache for assistant cognition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..protocol.auraCategories import AuraCategories


@dataclass(slots=True)
class BridgeStateCache:
    """Cache bridge state without taking authority away from the bridge."""

    context: Any = None
    connected: bool = False
    bridgeName: str = "Unavailable"
    lastError: str = ""
    lastMessage: dict[str, Any] = field(default_factory=dict)
    contextData: dict[str, Any] = field(default_factory=dict)
    devices: list[dict[str, Any]] = field(default_factory=list)
    lights: list[dict[str, Any]] = field(default_factory=list)
    cameras: list[dict[str, Any]] = field(default_factory=list)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    notifications: list[dict[str, Any]] = field(default_factory=list)
    streams: dict[str, dict[str, Any]] = field(default_factory=dict)
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def updateMessage(self, message) -> dict[str, Any]:
        """Cache one inbound protocol message."""

        payload = message.toDict() if hasattr(message, "toDict") else dict(message)
        self.lastMessage = payload
        category = str(payload.get("category") or "")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        context = payload.get("context") if isinstance(payload.get("context"), dict) else {}

        if category == AuraCategories.ASSISTANT_CONTEXT:
            self.contextData.update(data)
            self.sessions.update(self._normalizeSessionContext(context, data))
            self.connected = bool(data.get("connected", True)) or self.connected
            self.bridgeName = str(data.get("bridgeName") or data.get("bridge_name") or self.bridgeName)
        elif category == AuraCategories.ASSISTANT_NOTIFICATION:
            self.notifications.append(dict(data))
        elif category == AuraCategories.ASSISTANT_STREAM_AVAILABLE:
            stream_id = str(data.get("streamId") or "")
            if stream_id:
                self.streams[stream_id] = dict(data)
        elif category == AuraCategories.ASSISTANT_RESPONSE:
            request_id = str(data.get("requestId") or payload.get("requestId") or "")
            if request_id:
                self.responses[request_id] = dict(data)
            self._mergeStatePayload(data.get("state"))
            self._mergeStatePayload(data.get("bridgeState"))
        elif category == AuraCategories.ASSISTANT_ERROR:
            self.lastError = str(data.get("message") or data.get("error") or self.lastError)
            self.errors.append(dict(data))

        return payload

    def setBridgeState(self, data: dict[str, Any]):
        """Replace the cached bridge state snapshot."""

        if not isinstance(data, dict):
            return
        self.connected = bool(data.get("connected", self.connected))
        self.bridgeName = str(data.get("bridgeName") or data.get("bridge_name") or self.bridgeName)
        self.lastError = str(data.get("lastError") or data.get("last_error") or self.lastError)
        self.contextData.update(data)
        self._mergeStatePayload(data)

    def getResponse(self, requestId: str) -> dict[str, Any] | None:
        """Return a cached response by request id."""

        return self.responses.get(requestId)

    def getNotificationContext(self) -> list[dict[str, Any]]:
        """Return assistant notifications as plain dictionaries."""

        return list(self.notifications)

    def snapshot(self) -> dict[str, Any]:
        """Return a compact assistant-facing bridge snapshot."""

        return {
            "connected": self.connected,
            "bridgeName": self.bridgeName,
            "lastError": self.lastError,
            "context": dict(self.contextData),
            "devices": list(self.devices),
            "lights": list(self.lights),
            "cameras": list(self.cameras),
            "notifications": list(self.notifications),
            "streams": list(self.streams.values()),
            "sessions": list(self.sessions.values()),
        }

    def _normalizeSessionContext(self, context: dict[str, Any], data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Normalize a session block from bridge context payloads."""

        session_id = str(context.get("sessionId") or data.get("sessionId") or "").strip()
        interface = str(context.get("interface") or data.get("interface") or "").strip()
        if not session_id:
            return {}
        session = dict(context)
        session.update(data)
        session["sessionId"] = session_id
        if interface:
            session["interface"] = interface
        return {session_id: session}

    def _mergeStatePayload(self, payload):
        """Merge bridge device state payloads into cached assistant state."""

        if not isinstance(payload, dict):
            return
        self.connected = bool(payload.get("connected", self.connected))
        self.bridgeName = str(payload.get("bridgeName") or payload.get("bridge_name") or self.bridgeName)
        self.lastError = str(payload.get("lastError") or payload.get("last_error") or self.lastError)
        self.contextData.update(payload)

        if isinstance(payload.get("devices"), list):
            self.devices = [dict(item) for item in payload["devices"] if isinstance(item, dict)]
        if isinstance(payload.get("lights"), list):
            self.lights = [dict(item) for item in payload["lights"] if isinstance(item, dict)]
        if isinstance(payload.get("cameras"), list):
            self.cameras = [dict(item) for item in payload["cameras"] if isinstance(item, dict)]
