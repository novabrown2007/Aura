"""Executable action payload attached to structured assistant responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResponseAction:
    """Describe one executable assistant action."""

    actionName: str = ""
    target: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    source: str = ""
    requiresExecution: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "actionName": self.actionName,
            "target": self.target,
            "arguments": dict(self.arguments or {}),
            "description": self.description,
            "source": self.source,
            "requiresExecution": bool(self.requiresExecution),
            "metadata": dict(self.metadata or {}),
        }
