"""Task definition metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any

from .retryPolicy import RetryPolicy
from .taskPriority import TaskPriority


@dataclass
class TaskDefinition:
    """Describe a reusable task template."""

    taskName: str = ""
    taskType: str = "callable"
    handler: Callable[..., Any] | None = None
    priority: str = TaskPriority.NORMAL
    retryPolicy: RetryPolicy = field(default_factory=RetryPolicy)
    metadata: dict = field(default_factory=dict)
    asyncSupported: bool = True

    def asDict(self) -> dict:
        return {
            "taskName": self.taskName,
            "taskType": self.taskType,
            "priority": self.priority,
            "retryPolicy": self.retryPolicy.asDict() if hasattr(self.retryPolicy, "asDict") else dict(self.retryPolicy or {}),
            "metadata": dict(self.metadata or {}),
            "asyncSupported": bool(self.asyncSupported),
        }
