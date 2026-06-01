"""Normalized task execution result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskResult:
    """Represent the outcome of one task execution."""

    taskId: str = ""
    status: str = "PENDING"
    result: Any = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    executionTime: float = 0.0
    metadata: dict = field(default_factory=dict)

    def asDict(self) -> dict:
        return {
            "taskId": self.taskId,
            "status": self.status,
            "result": self.result,
            "errors": list(self.errors or []),
            "warnings": list(self.warnings or []),
            "executionTime": float(self.executionTime),
            "metadata": dict(self.metadata or {}),
        }
