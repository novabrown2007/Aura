"""Scheduled task wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

from .auraTask import AuraTask


@dataclass
class ScheduledTask:
    """Wrap a task and its planned run time."""

    scheduledTaskId: str = ""
    task: AuraTask | None = None
    scheduledAt: str = ""
    state: str = "PENDING"
    metadata: dict = field(default_factory=dict)

    def asDict(self) -> dict:
        return {
            "scheduledTaskId": self.scheduledTaskId,
            "task": self.task.asDict() if hasattr(self.task, "asDict") else None,
            "scheduledAt": self.scheduledAt,
            "state": self.state,
            "metadata": dict(self.metadata or {}),
        }
