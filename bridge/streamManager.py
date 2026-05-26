"""Stream metadata handling for Aura Protocol messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .protocol.auraCategories import AuraCategories


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AuraStream:
    """Normalized stream metadata."""

    streamId: str
    streamType: str
    endpoint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    sessionId: str = ""
    interface: str = ""
    status: str = "available"
    createdAt: str = field(default_factory=_now)
    updatedAt: str = field(default_factory=_now)


class StreamRegistry:
    """Store and expose assistant-visible stream metadata."""

    def __init__(self, context=None):
        self.context = context
        self.streams: dict[str, AuraStream] = {}

    def register(self, stream: AuraStream) -> AuraStream:
        """Add or replace a stream entry."""

        stream.updatedAt = _now()
        if not stream.createdAt:
            stream.createdAt = stream.updatedAt
        self.streams[stream.streamId] = stream
        return stream

    def update(self, streamId: str, **updates: Any) -> AuraStream | None:
        """Update a known stream."""

        stream = self.streams.get(streamId)
        if stream is None:
            return None
        for key, value in updates.items():
            if hasattr(stream, key):
                setattr(stream, key, value)
        stream.updatedAt = _now()
        return stream

    def remove(self, streamId: str) -> bool:
        """Delete a stream entry."""

        return self.streams.pop(streamId, None) is not None

    def get(self, streamId: str) -> AuraStream | None:
        """Return one stream entry."""

        return self.streams.get(streamId)

    def list(self) -> list[AuraStream]:
        """Return all stream entries."""

        return list(self.streams.values())


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
