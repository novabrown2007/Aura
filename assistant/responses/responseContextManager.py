"""Runtime context attachment for structured assistant responses."""

from __future__ import annotations

from assistant.responses.models import ResponseContext


class ResponseContextManager:
    """Collect conversation, memory, and interface state for a response."""

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Responses.Context") if logger else None
        self.lastContext = ResponseContext()

    def buildContext(self, userInput: str = "", provider=None) -> ResponseContext:
        conversation = self._snapshot("conversationManager")
        memory = self._snapshot("memoryManager")
        interface = self._snapshot("desktopOverlayManager")
        interruption = self._snapshot("interruptionManager")
        sessionId = ""
        session = getattr(self.context, "sessionManager", None)
        if session is not None and hasattr(session, "currentSessionId"):
            sessionId = str(getattr(session, "currentSessionId", "") or "")

        responseContext = ResponseContext(
            conversation=conversation,
            memory=memory,
            interface=interface,
            interruption=interruption,
            sessionId=sessionId,
            userInput=str(userInput or ""),
        )
        self.lastContext = responseContext
        return responseContext

    def updateFromEvent(self, eventName: str, payload: dict | None = None):
        """Capture recent orchestration signals for later response packets."""

        payload = dict(payload or {})
        self.lastContext.interface.setdefault("recentEvent", eventName)
        self.lastContext.interface["recentPayload"] = payload
        if eventName == "memory.retrieved":
            self.lastContext.memory["lastRetrieval"] = payload
        if eventName.startswith("conversation."):
            self.lastContext.conversation["lastEvent"] = eventName
            self.lastContext.conversation["lastPayload"] = payload
        return self.lastContext

    def snapshot(self) -> dict:
        return self.lastContext.asDict()

    def _snapshot(self, attribute: str) -> dict:
        manager = getattr(self.context, attribute, None)
        if manager is None:
            return {}
        if hasattr(manager, "snapshot"):
            try:
                snapshot = manager.snapshot()
                return dict(snapshot or {})
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Response context snapshot failed for {attribute}: {error}")
        return {"available": True, "class": manager.__class__.__name__}
