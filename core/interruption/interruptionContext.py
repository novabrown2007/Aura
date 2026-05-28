"""Context object for one interruption execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.interruption.models.interruptionRequest import InterruptionRequest


@dataclass
class InterruptionContext:
    """Track metadata and results for a single interruption."""

    request: InterruptionRequest
    interruptedOperations: list[str] = field(default_factory=list)
    failedOperations: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    startedAt: str = field(default_factory=lambda: datetime.now().isoformat(timespec="milliseconds"))
    completedAt: str = ""

    def markCancelled(self, operationId: str):
        """Record a cancelled operation."""

        if operationId not in self.interruptedOperations:
            self.interruptedOperations.append(operationId)

    def markFailed(self, operationId: str, error: str):
        """Record an operation cancellation failure."""

        self.failedOperations.append({"operationId": operationId, "error": str(error)})

    def complete(self):
        """Mark this context complete."""

        self.completedAt = datetime.now().isoformat(timespec="milliseconds")

    def asDict(self) -> dict:
        """Return a serializable context payload."""

        return {
            "request": self.request.asDict(),
            "interruptedOperations": list(self.interruptedOperations),
            "failedOperations": list(self.failedOperations),
            "metadata": dict(self.metadata or {}),
            "startedAt": self.startedAt,
            "completedAt": self.completedAt,
        }

