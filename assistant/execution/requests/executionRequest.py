"""Canonical execution request."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from assistant.execution.executionContext import ExecutionContext
from assistant.execution.requests.executionMetadata import ExecutionMetadata


@dataclass
class ExecutionRequest:
    """Describe one execution request before routing."""

    requestId: str = field(default_factory=lambda: uuid4().hex)
    intent: str = ""
    action: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    source: str = "SYSTEM"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    conversationId: str = ""
    requestedBy: str = ""
    metadata: ExecutionMetadata | dict[str, Any] = field(default_factory=ExecutionMetadata)
    executionContext: ExecutionContext = field(default_factory=ExecutionContext)

    def asDict(self) -> dict[str, Any]:
        metadata = self.metadata.asDict() if hasattr(self.metadata, "asDict") else dict(self.metadata or {})
        return {
            "requestId": self.requestId,
            "intent": self.intent,
            "action": self.action,
            "parameters": dict(self.parameters or {}),
            "source": self.source,
            "timestamp": self.timestamp,
            "conversationId": self.conversationId,
            "requestedBy": self.requestedBy,
            "metadata": metadata,
            "executionContext": self.executionContext.asDict() if hasattr(self.executionContext, "asDict") else dict(self.executionContext or {}),
        }
