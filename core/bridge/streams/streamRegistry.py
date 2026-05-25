"""Stream registry for assistant-facing stream metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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

