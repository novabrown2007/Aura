"""Confirmation request model for Aura governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class ConfirmationRequest:
    """Track one pending dangerous action confirmation."""

    requestId: str = field(default_factory=lambda: uuid4().hex)
    prompt: str = ""
    request: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    createdAt: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    timeoutSeconds: int = 60
    acknowledged: bool = False

    def asDict(self) -> dict[str, Any]:
        return {
            "requestId": self.requestId,
            "prompt": self.prompt,
            "request": dict(self.request or {}),
            "decision": dict(self.decision or {}),
            "createdAt": self.createdAt,
            "timeoutSeconds": int(self.timeoutSeconds),
            "acknowledged": bool(self.acknowledged),
        }

