"""Handle assistant.context messages."""

from __future__ import annotations

from ..protocol.auraCategories import AuraCategories


class ContextHandler:
    """Normalize assistant context into the local cache and runtime bus."""

    def __init__(self, context, stateCache):
        self.context = context
        self.stateCache = stateCache
        self.logger = context.logger.getChild("Bridge.Context") if getattr(context, "logger", None) else None

    def handle(self, message):
        """Handle one assistant.context message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_CONTEXT:
            return None
        payload = self.stateCache.updateMessage(message)
        self._emit(payload)
        return payload

    def _emit(self, payload: dict):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is not None:
            event_manager.emit(AuraCategories.ASSISTANT_CONTEXT, payload)

