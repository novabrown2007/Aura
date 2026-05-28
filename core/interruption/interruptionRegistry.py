"""Registry for interruptible Aura systems and operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Callable


@dataclass
class InterruptibleOperation:
    """Metadata for one active interruptible operation."""

    operationId: str
    systemName: str
    operationType: str
    cancelHandler: Callable | None = None
    metadata: dict = field(default_factory=dict)
    startedAt: str = field(default_factory=lambda: datetime.now().isoformat(timespec="milliseconds"))

    def asDict(self) -> dict:
        """Return serializable operation metadata."""

        return {
            "operationId": self.operationId,
            "systemName": self.systemName,
            "operationType": self.operationType,
            "metadata": dict(self.metadata or {}),
            "startedAt": self.startedAt,
        }


class InterruptionRegistry:
    """Track interruptible systems, operations, and cancellation handlers."""

    def __init__(self, context=None):
        self.context = context
        self.handlers: dict[str, object] = {}
        self.operations: dict[str, InterruptibleOperation] = {}
        self._lock = RLock()
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption.Registry") if logger else None

    def registerHandler(self, systemName: str, handler):
        """Register a system-level interruption handler."""

        with self._lock:
            self.handlers[str(systemName)] = handler

    def unregisterHandler(self, systemName: str):
        """Remove a registered handler."""

        with self._lock:
            self.handlers.pop(str(systemName), None)

    def registerOperation(
        self,
        operationId: str,
        systemName: str,
        operationType: str,
        cancelHandler: Callable | None = None,
        metadata: dict | None = None,
    ):
        """Register an active interruptible operation."""

        with self._lock:
            self.operations[operationId] = InterruptibleOperation(
                operationId=operationId,
                systemName=systemName,
                operationType=operationType,
                cancelHandler=cancelHandler,
                metadata=metadata or {},
            )

    def completeOperation(self, operationId: str):
        """Remove an operation after completion."""

        with self._lock:
            self.operations.pop(operationId, None)

    def getOperations(self, operationTypes: set[str] | None = None) -> list[InterruptibleOperation]:
        """Return active operations, optionally filtered by type."""

        with self._lock:
            operations = list(self.operations.values())
        if operationTypes:
            operations = [item for item in operations if item.operationType in operationTypes]
        return operations

    def getHandlers(self) -> dict[str, object]:
        """Return registered handlers."""

        with self._lock:
            return dict(self.handlers)

    def snapshot(self) -> dict:
        """Return registry diagnostics."""

        return {
            "handlers": sorted(self.handlers.keys()),
            "operations": [operation.asDict() for operation in self.getOperations()],
        }

