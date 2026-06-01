"""Track execution lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionStateRecord:
    """State of one active execution."""

    requestId: str
    action: str
    status: str = "PENDING"
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionStateManager:
    """Maintain active and completed execution state."""

    def __init__(self, context=None):
        self.context = context
        self.active: dict[str, ExecutionStateRecord] = {}
        self.completed: list[ExecutionStateRecord] = []

    def start(self, request):
        metadata = getattr(request, "metadata", {}) or {}
        if hasattr(metadata, "asDict"):
            metadata = metadata.asDict()
        record = ExecutionStateRecord(
            requestId=str(getattr(request, "requestId", "") or ""),
            action=str(getattr(request, "action", "") or ""),
            status="VALIDATING",
            metadata=dict(metadata or {}),
        )
        self.active[record.requestId] = record
        return record

    def update(self, requestId: str, status: str, **metadata):
        record = self.active.get(str(requestId))
        if record is None:
            return None
        record.status = status
        record.metadata.update(metadata)
        if status in {"COMPLETED", "FAILED", "DENIED", "TIMEOUT", "CANCELLED"}:
            self.completed.append(record)
            self.active.pop(record.requestId, None)
        return record

    def snapshot(self):
        return {
            "active": {requestId: record.__dict__ for requestId, record in self.active.items()},
            "completed": [record.__dict__ for record in self.completed[-25:]],
        }
