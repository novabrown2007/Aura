"""Stream metadata handling for Aura Protocol messages."""

from __future__ import annotations

from typing import Any

from ..protocol.auraCategories import AuraCategories
from .streamRegistry import AuraStream, StreamRegistry


class StreamManager:
    """Track bridge-exposed stream metadata only, not transport internals."""

    def __init__(self, context=None, registry: StreamRegistry | None = None):
        self.context = context
        self.registry = registry or StreamRegistry(context)

    def registerStream(self, streamId: str, streamType: str, endpoint: str = "", metadata: dict[str, Any] | None = None, sessionId: str = "", interface: str = "") -> AuraStream:
        """Register or replace one stream record."""

        stream = AuraStream(
            streamId=str(streamId),
            streamType=str(streamType),
            endpoint=str(endpoint or ""),
            metadata=dict(metadata or {}),
            sessionId=str(sessionId or ""),
            interface=str(interface or ""),
        )
        return self.registry.register(stream)

    def handleMessage(self, message) -> AuraStream | None:
        """Normalize an Aura stream.available message into the registry."""

        category = getattr(message, "category", "")
        if category != AuraCategories.ASSISTANT_STREAM_AVAILABLE:
            return None

        data = getattr(message, "data", {}) or {}
        stream = self.registerStream(
            streamId=data.get("streamId", ""),
            streamType=data.get("streamType", ""),
            endpoint=data.get("endpoint", ""),
            metadata={key: value for key, value in data.items() if key not in {"streamId", "streamType", "endpoint"}},
            sessionId=str(getattr(message, "context", {}).get("sessionId", "")),
            interface=str(getattr(message, "context", {}).get("interface", "")),
        )
        return stream

    def getStream(self, streamId: str) -> AuraStream | None:
        """Return one stream record."""

        return self.registry.get(streamId)

    def listStreams(self) -> list[AuraStream]:
        """Return all registered streams."""

        return self.registry.list()

