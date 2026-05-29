"""Injected runtime context wrapper for Aura modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModuleContext:
    """Read-only view of the shared Aura runtime for a module."""

    runtime: Any
    metadata: Any

    @property
    def logger(self):
        """Return a module-scoped child logger when available."""

        logger = getattr(self.runtime, "logger", None)
        if logger is None:
            return None
        return logger.getChild(getattr(self.metadata, "name", "module"))

    @property
    def eventBus(self):
        """Return the shared event bus."""

        return getattr(self.runtime, "eventManager", None)

    @property
    def config(self):
        """Return the shared configuration object."""

        return getattr(self.runtime, "config", None)

    @property
    def memory(self):
        """Return the shared memory manager."""

        return getattr(self.runtime, "memoryManager", None)

    @property
    def providers(self):
        """Return the shared provider manager, if available."""

        return getattr(self.runtime, "llmManager", None)

    @property
    def tools(self):
        """Return the shared tool registry."""

        return getattr(self.runtime, "toolRegistry", None)

    @property
    def assistant(self):
        """Return the assistant-layer services container."""

        return getattr(self.runtime, "assistant", None)

    def emit(self, eventName: str, data: dict[str, Any] | None = None):
        """Emit a runtime event through the shared bus."""

        eventBus = self.eventBus
        if eventBus is None:
            return None
        return eventBus.emit(eventName, data or {})

    def subscribe(self, eventName: str, handler):
        """Subscribe a handler to a shared event bus event."""

        eventBus = self.eventBus
        if eventBus is None:
            return None
        return eventBus.subscribe(eventName, handler)

    def unsubscribe(self, eventName: str, handler):
        """Unsubscribe a handler from a shared event bus event."""

        eventBus = self.eventBus
        if eventBus is None:
            return None
        return eventBus.unsubscribe(eventName, handler)
