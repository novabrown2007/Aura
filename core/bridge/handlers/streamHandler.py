"""Handle assistant.stream.available messages."""

from __future__ import annotations

from ..protocol.auraCategories import AuraCategories


class StreamHandler:
    """Normalize stream metadata and expose it to the runtime."""

    def __init__(self, context, streamManager, stateCache):
        self.context = context
        self.streamManager = streamManager
        self.stateCache = stateCache
        self.logger = context.logger.getChild("Bridge.Stream") if getattr(context, "logger", None) else None

    def handle(self, message):
        """Handle one assistant.stream.available message."""

        if getattr(message, "category", "") != AuraCategories.ASSISTANT_STREAM_AVAILABLE:
            return None
        self.stateCache.updateMessage(message)
        stream = self.streamManager.handleMessage(message)
        self._emit(stream, message)
        return stream

    def _emit(self, stream, message):
        event_manager = getattr(self.context, "eventManager", None)
        if event_manager is not None and stream is not None:
            event_manager.emit(
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

