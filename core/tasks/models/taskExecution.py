"""Execution tracking for task lifecycle attempts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskExecution:
    """Track one task run and its attempts."""

    executionId: str = ""
    taskId: str = ""
    attempts: int = 0
    startedAt: str = ""
    completedAt: str = ""
    state: str = "PENDING"
    result: Any = None
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def asDict(self) -> dict:
        return {
            "executionId": self.executionId,
            "taskId": self.taskId,
            "attempts": int(self.attempts),
            "startedAt": self.startedAt,
            "completedAt": self.completedAt,
            "state": self.state,
            "result": self.result,
            "errors": list(self.errors or []),
            "metadata": dict(self.metadata or {}),
        }
