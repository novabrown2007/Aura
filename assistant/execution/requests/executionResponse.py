"""Execution response payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionResponse:
    """Normalized result returned by the execution pipeline."""

    requestId: str = ""
    status: str = "FAILED"
    result: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    executionTime: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def asDict(self) -> dict[str, Any]:
        return {
            "requestId": self.requestId,
            "status": self.status,
            "result": self.result,
            "errors": list(self.errors or []),
            "warnings": list(self.warnings or []),
            "executionTime": float(self.executionTime or 0.0),
            "metadata": dict(self.metadata or {}),
        }
