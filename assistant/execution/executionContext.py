"""Runtime context passed through the execution pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    """Container for contextual execution dependencies."""

    conversationContext: dict[str, Any] = field(default_factory=dict)
    moduleContext: dict[str, Any] = field(default_factory=dict)
    runtimeContext: dict[str, Any] = field(default_factory=dict)
    userContext: dict[str, Any] = field(default_factory=dict)
    source: str = "SYSTEM"
    permissionState: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "conversationContext": dict(self.conversationContext or {}),
            "moduleContext": dict(self.moduleContext or {}),
            "runtimeContext": dict(self.runtimeContext or {}),
            "userContext": dict(self.userContext or {}),
            "source": self.source,
            "permissionState": dict(self.permissionState or {}),
            "metadata": dict(self.metadata or {}),
        }
