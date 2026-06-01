"""Context associated with an execution request."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionContext:
    """Runtime context for one proposed action."""

    conversation: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)
    interface: dict[str, Any] = field(default_factory=dict)
    automation: dict[str, Any] = field(default_factory=dict)
    trust: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "conversation": dict(self.conversation or {}),
            "memory": dict(self.memory or {}),
            "interface": dict(self.interface or {}),
            "automation": dict(self.automation or {}),
            "trust": dict(self.trust or {}),
            "metadata": dict(self.metadata or {}),
        }

