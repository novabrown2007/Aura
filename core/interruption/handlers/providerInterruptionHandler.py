"""Provider interruption handler."""

from __future__ import annotations


class ProviderInterruptionHandler:
    """Request cancellation for provider operations."""

    systemName = "provider"

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption.Provider") if logger else None

    def cancel(self, interruptionContext) -> list[str]:
        """Cancel provider operations through manager hooks when available."""

        cancelled = []
        manager = getattr(self.context, "llmManager", None)
        try:
            if manager is not None and hasattr(manager, "cancelActiveRequests"):
                manager.cancelActiveRequests()
                cancelled.append("provider.requests")
        except Exception as error:
            interruptionContext.markFailed("provider.requests", str(error))
        return cancelled

