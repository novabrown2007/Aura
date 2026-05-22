"""Handle assistant.response messages."""

from __future__ import annotations

from ..protocol.auraCategories import AuraCategories


class ResponseHandler:
    """Cache assistant responses and release pending requests."""

    def __init__(self, context, stateCache):
        self.context = context
        self.stateCache = stateCache
        self.logger = context.logger.getChild("Bridge.Response") if getattr(context, "logger", None) else None

    def handle(self, message):
        """Handle one assistant.response message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_RESPONSE:
            return None
        payload = self.stateCache.updateMessage(message)
        self._release(message, payload)
        return payload

    def _release(self, message, payload: dict):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is not None:
            event_manager.emit(AuraCategories.ASSISTANT_RESPONSE, payload)

        client = getattr(self.context, "bridgeClient", None) or getattr(self.context, "auraBridgeClient", None)
        if client is not None and hasattr(client, "completePendingRequest"):
            request_id = str(getattr(message, "data", {}).get("requestId") or getattr(message, "requestId", ""))
            if request_id:
                client.completePendingRequest(request_id, payload)

