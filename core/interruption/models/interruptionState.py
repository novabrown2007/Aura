"""Interruption state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InterruptionState:
    """Current and recent interruption state for diagnostics."""

    active: bool = False
    currentRequestId: str = ""
    currentType: str = ""
    source: str = ""
    startedAt: str = ""
    completedAt: str = ""
    cancelledOperations: list[str] = field(default_factory=list)
    failedOperations: list[dict] = field(default_factory=list)
    lastPhrase: str = ""

    def start(self, request):
        """Mark an interruption as active."""

        self.active = True
        self.currentRequestId = request.requestId
        self.currentType = request.interruptionType
        self.source = request.source
        self.startedAt = datetime.now().isoformat(timespec="milliseconds")
        self.completedAt = ""
        self.cancelledOperations = []
        self.failedOperations = []
        self.lastPhrase = request.phrase

    def complete(self):
        """Mark the active interruption as complete."""

        self.active = False
        self.completedAt = datetime.now().isoformat(timespec="milliseconds")

    def asDict(self) -> dict:
        """Return a serializable state payload."""

        return {
            "active": self.active,
            "currentRequestId": self.currentRequestId,
            "currentType": self.currentType,
            "source": self.source,
            "startedAt": self.startedAt,
            "completedAt": self.completedAt,
            "cancelledOperations": list(self.cancelledOperations),
            "failedOperations": list(self.failedOperations),
            "lastPhrase": self.lastPhrase,
        }

