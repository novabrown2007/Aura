"""Handle assistant.error messages."""

from __future__ import annotations

from ..protocol.auraCategories import AuraCategories


class ErrorHandler:
    """Normalize assistant errors and surface them to the runtime."""

    def __init__(self, context, stateCache):
        self.context = context
        self.stateCache = stateCache
        self.logger = context.logger.getChild("Bridge.Error") if getattr(context, "logger", None) else None

    def handle(self, message):
        """Handle one assistant.error message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_ERROR:
            return None
        payload = self.stateCache.updateMessage(message)
        self._emit(payload)
        return payload

    def _emit(self, payload: dict):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is not None:
            event_manager.emit(AuraCategories.ASSISTANT_ERROR, payload)

