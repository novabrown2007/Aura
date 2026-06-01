"""Execution request model for Aura governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from assistant.safety.models.executionContext import ExecutionContext


@dataclass
class ExecutionRequest:
    """Describe one requested action before it can execute."""

    requestId: str = field(default_factory=lambda: uuid4().hex)
    source: str = ""
    module: str = ""
    action: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    executionContext: ExecutionContext = field(default_factory=ExecutionContext)
    requestedBy: str = ""
    priority: str = "NORMAL"
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "requestId": self.requestId,
            "source": self.source,
            "module": self.module,
            "action": self.action,
            "parameters": dict(self.parameters or {}),
            "timestamp": self.timestamp,
            "executionContext": self.executionContext.asDict() if hasattr(self.executionContext, "asDict") else dict(self.executionContext or {}),
            "requestedBy": self.requestedBy,
            "priority": self.priority,
            "metadata": dict(self.metadata or {}),
        }

