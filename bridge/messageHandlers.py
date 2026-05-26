"""Inbound Aura Protocol message handlers.

These handlers intentionally stay small: they normalize bridge messages into
Aura runtime state, then emit the corresponding internal event.
"""

from __future__ import annotations

from .protocol.auraCategories import AuraCategories


class _BaseMessageHandler:
    """Shared event emission helper for bridge message handlers."""

    def __init__(self, context, stateCache, loggerName: str):
        self.context = context
        self.stateCache = stateCache
        self.logger = context.logger.getChild(loggerName) if getattr(context, "logger", None) else None

    def _emit(self, eventName: str, payload: dict):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is not None:
            eventManager.emit(eventName, payload)


class ContextHandler(_BaseMessageHandler):
    """Normalize assistant context into the local cache and runtime bus."""

    def __init__(self, context, stateCache):
        super().__init__(context, stateCache, "Bridge.Context")

    def handle(self, message):
        """Handle one assistant.context message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_CONTEXT:
            return None
        payload = self.stateCache.updateMessage(message)
        self._emit(AuraCategories.ASSISTANT_CONTEXT, payload)
        return payload


class ErrorHandler(_BaseMessageHandler):
    """Normalize assistant errors and surface them to the runtime."""

    def __init__(self, context, stateCache):
        super().__init__(context, stateCache, "Bridge.Error")

    def handle(self, message):
        """Handle one assistant.error message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_ERROR:
            return None
        payload = self.stateCache.updateMessage(message)
        self._emit(AuraCategories.ASSISTANT_ERROR, payload)
        return payload


class NotificationHandler(_BaseMessageHandler):
    """Record assistant-facing notifications and expose them to Aura."""

    def __init__(self, context, notificationManager, stateCache):
        super().__init__(context, stateCache, "Bridge.Notification")
        self.notificationManager = notificationManager

    def handle(self, message):
        """Handle one assistant.notification message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_NOTIFICATION:
            return None
        self.stateCache.updateMessage(message)
        notification = self.notificationManager.record(message)
        if notification is not None:
            self._emit(
                AuraCategories.ASSISTANT_NOTIFICATION,
                {
                    "event": notification.event,
                    "location": notification.location,
                    "priority": notification.priority,
                    "source": notification.source,
                    "data": notification.data,
                    "sessionId": notification.sessionId,
                    "interface": notification.interface,
                },
            )
        return notification


class ResponseHandler(_BaseMessageHandler):
    """Cache assistant responses and release pending requests."""

    def __init__(self, context, stateCache):
        super().__init__(context, stateCache, "Bridge.Response")

    def handle(self, message):
        """Handle one assistant.response message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_RESPONSE:
            return None
        payload = self.stateCache.updateMessage(message)
        self._emit(AuraCategories.ASSISTANT_RESPONSE, payload)

        client = getattr(self.context, "bridgeClient", None) or getattr(self.context, "auraBridgeClient", None)
        if client is not None and hasattr(client, "completePendingRequest"):
            requestId = str(getattr(message, "data", {}).get("requestId") or getattr(message, "requestId", ""))
            if requestId:
                client.completePendingRequest(requestId, payload)
        return payload


class StreamHandler(_BaseMessageHandler):
    """Normalize stream metadata and expose it to the runtime."""

    def __init__(self, context, streamManager, stateCache):
        super().__init__(context, stateCache, "Bridge.Stream")
        self.streamManager = streamManager

    def handle(self, message):
        """Handle one assistant.stream.available message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_STREAM_AVAILABLE:
            return None
        self.stateCache.updateMessage(message)
        stream = self.streamManager.handleMessage(message)
        if stream is not None:
            self._emit(
                AuraCategories.ASSISTANT_STREAM_AVAILABLE,
                {
                    "streamId": stream.streamId,
                    "streamType": stream.streamType,
                    "endpoint": stream.endpoint,
                    "metadata": stream.metadata,
                    "sessionId": stream.sessionId,
                    "interface": stream.interface,
                    "status": stream.status,
                },
            )
        return stream
