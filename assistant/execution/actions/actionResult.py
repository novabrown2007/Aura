"""Execution result container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    """Normalized result from one action execution."""

    status: str = "COMPLETED"
    result: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "result": self.result,
            "errors": list(self.errors or []),
            "warnings": list(self.warnings or []),
            "metadata": dict(self.metadata or {}),
        }

