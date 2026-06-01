"""One active clarification session."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any
from uuid import uuid4

from assistant.clarification.models.clarificationRequest import ClarificationRequest
from assistant.clarification.models.clarificationState import ClarificationState


@dataclass(slots=True)
class ClarificationSession:
    """Track one pending clarification and its continuation state."""

    sessionId: str = field(default_factory=lambda: uuid4().hex)
    activeRequest: ClarificationRequest | dict[str, Any] = field(default_factory=ClarificationRequest)
    conversationContext: dict[str, Any] = field(default_factory=dict)
    pendingIntent: dict[str, Any] = field(default_factory=dict)
    pendingAction: dict[str, Any] = field(default_factory=dict)
    state: ClarificationState = ClarificationState.PENDING
    createdAt: float = field(default_factory=time)
    updatedAt: float = field(default_factory=time)
    attempts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self):
        self.updatedAt = time()

    def asDict(self) -> dict[str, Any]:
        request = self.activeRequest.asDict() if hasattr(self.activeRequest, "asDict") else dict(self.activeRequest or {})
        return {
            "sessionId": self.sessionId,
            "activeRequest": request,
            "conversationContext": dict(self.conversationContext or {}),
            "pendingIntent": dict(self.pendingIntent or {}),
            "pendingAction": dict(self.pendingAction or {}),
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "attempts": int(self.attempts or 0),
            "metadata": dict(self.metadata or {}),
        }
