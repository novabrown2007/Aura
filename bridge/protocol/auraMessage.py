"""Protocol message representation used by the Aura assistant bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_timestamp() -> str:
    """Return a stable UTC timestamp string."""

    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AuraMessage:
    """Deterministic Aura Protocol message envelope."""

    category: str
    data: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    messageId: str = field(default_factory=lambda: uuid4().hex)
    requestId: str = ""
    timestamp: str = field(default_factory=_utc_timestamp)

    def toDict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""

        payload = {
            "category": self.category,
            "data": dict(self.data),
            "context": dict(self.context),
            "source": dict(self.source),
            "messageId": self.messageId,
            "timestamp": self.timestamp,
        }
        if self.requestId:
            payload["requestId"] = self.requestId
        return payload

    @classmethod
    def fromDict(cls, payload: dict[str, Any]):
        """Build a message from a raw dictionary."""

        return cls(
            category=str(payload.get("category") or ""),
            data=payload.get("data") if isinstance(payload.get("data"), dict) else {},
            context=payload.get("context") if isinstance(payload.get("context"), dict) else {},
            source=payload.get("source") if isinstance(payload.get("source"), dict) else {},
            messageId=str(payload.get("messageId") or payload.get("message_id") or uuid4().hex),
            requestId=str(payload.get("requestId") or payload.get("request_id") or ""),
            timestamp=str(payload.get("timestamp") or _utc_timestamp()),
        )

    def withContext(self, **contextUpdates: Any):
        """Return a copy with updated context data."""

        context = dict(self.context)
        context.update(contextUpdates)
        return AuraMessage(
            category=self.category,
            data=dict(self.data),
            context=context,
            source=dict(self.source),
            messageId=self.messageId,
            requestId=self.requestId,
            timestamp=self.timestamp,
        )

