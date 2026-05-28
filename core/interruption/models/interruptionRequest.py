"""Interruption request model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class InterruptionRequest:
    """A user/system request to interrupt active Aura operations."""

    interruptionType: str = "GLOBAL_CANCEL"
    source: str = "runtime"
    phrase: str = ""
    scope: str = "global"
    reason: str = ""
    metadata: dict = field(default_factory=dict)
    requestId: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="milliseconds"))

    def asDict(self) -> dict:
        """Return a serializable request payload."""

        return {
            "requestId": self.requestId,
            "interruptionType": self.interruptionType,
            "source": self.source,
            "phrase": self.phrase,
            "scope": self.scope,
            "reason": self.reason,
            "metadata": dict(self.metadata or {}),
            "timestamp": self.timestamp,
        }

