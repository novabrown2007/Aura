"""Cooperative cancellation token management for Aura."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, RLock
from uuid import uuid4


@dataclass
class CancellationToken:
    """A cooperative cancellation token for long-running operations."""

    operationId: str
    _event: Event = field(default_factory=Event)

    def cancel(self):
        """Request cancellation."""

        self._event.set()

    def clear(self):
        """Clear cancellation state for token reuse."""

        self._event.clear()

    @property
    def cancellationRequested(self) -> bool:
        """Return whether cancellation has been requested."""

        return self._event.is_set()


class CancellationManager:
    """Create and cancel cooperative operation tokens."""

    def __init__(self, context=None):
        self.context = context
        self.tokens: dict[str, CancellationToken] = {}
        self._lock = RLock()
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption.Cancellation") if logger else None

    def createToken(self, operationId: str | None = None) -> CancellationToken:
        """Create a cancellation token for an operation."""

        operationId = operationId or str(uuid4())
        with self._lock:
            token = CancellationToken(operationId)
            self.tokens[operationId] = token
            return token

    def getToken(self, operationId: str) -> CancellationToken | None:
        """Return a token by id."""

        with self._lock:
            return self.tokens.get(operationId)

    def cancel(self, operationId: str) -> bool:
        """Request cancellation for one token."""

        with self._lock:
            token = self.tokens.get(operationId)
            if token is None:
                return False
            token.cancel()
            if self.logger:
                self.logger.info(f"Cancellation requested for operation: {operationId}")
            return True

    def cancelAll(self) -> list[str]:
        """Request cancellation for all known tokens."""

        cancelled = []
        with self._lock:
            for operationId, token in self.tokens.items():
                token.cancel()
                cancelled.append(operationId)
        return cancelled

    def complete(self, operationId: str):
        """Remove a token after operation completion."""

        with self._lock:
            self.tokens.pop(operationId, None)

