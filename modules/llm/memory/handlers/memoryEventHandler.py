"""Event bus integration for structured long-term memory."""

from __future__ import annotations


class MemoryEventHandler:
    """Subscribe to Aura lifecycle events and trigger memory updates."""

    eventNames = (
        "conversation.started",
        "conversation.ended",
        "message.received",
        "response.generated",
        "session.created",
        "session.ended",
        "memory.created",
        "memory.updated",
        "memory.deleted",
        "memory.reindex.requested",
    )

    def __init__(self, context, memoryManager):
        self.context = context
        self.memoryManager = memoryManager
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Memory.Events") if logger else None
        self._subscribed = False
        self._sessionMessages: dict[str, list[tuple[str, str]]] = {}

    def subscribe(self):
        """Register handlers with Aura's event manager."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or self._subscribed:
            return
        for eventName in self.eventNames:
            eventManager.subscribe(eventName, self.handleEvent)
        self._subscribed = True
        if self.logger:
            self.logger.info("Memory event handler subscribed")

    def unsubscribe(self):
        """Remove handlers from Aura's event manager."""

        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None or not self._subscribed:
            return
        for eventName in self.eventNames:
            eventManager.unsubscribe(eventName, self.handleEvent)
        self._subscribed = False

    def handleEvent(self, event):
        """Route an Aura event into memory updates."""

        try:
            name = getattr(event, "name", "")
            data = getattr(event, "data", {}) or {}
            if name == "message.received":
                self._handleMessage(data)
            elif name == "response.generated":
                self._handleResponse(data)
            elif name in {"conversation.ended", "session.ended"}:
                self._handleConversationEnded(data)
            elif name == "session.created":
                self._handleSessionCreated(data)
            elif name in {"memory.created", "memory.updated"}:
                self._handleMemoryChanged(data)
            elif name == "memory.deleted":
                self._handleMemoryDeleted(data)
            elif name == "memory.reindex.requested":
                self._handleReindexRequested()
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Memory event handling failed: {error}")

    def _handleMessage(self, data: dict):
        text = str(data.get("text") or data.get("content") or data.get("message") or "").strip()
        sessionId = self._sessionId(data)
        if text:
            self._sessionMessages.setdefault(sessionId, []).append(("user", text))
            self.memoryManager.learnFromMessage(text, sessionId=sessionId)

    def _handleResponse(self, data: dict):
        text = str(data.get("text") or data.get("content") or data.get("response") or "").strip()
        sessionId = self._sessionId(data)
        if text:
            self._sessionMessages.setdefault(sessionId, []).append(("aura", text))

    def _handleConversationEnded(self, data: dict):
        sessionId = self._sessionId(data)
        messages = data.get("messages") or self._sessionMessages.get(sessionId, [])
        if messages:
            self.memoryManager.summarizeConversation(messages, sessionId=sessionId)
            self._sessionMessages.pop(sessionId, None)

    def _handleSessionCreated(self, data: dict):
        sessionId = self._sessionId(data)
        self._sessionMessages.setdefault(sessionId, [])

    def _handleMemoryChanged(self, data: dict):
        memoryManager = self.memoryManager
        embeddingManager = getattr(memoryManager, "memoryEmbeddingManager", None)
        if embeddingManager is None:
            return
        memory = getattr(memoryManager.store, "getMemory", lambda *_args, **_kwargs: None)(str(data.get("memoryId") or data.get("memory_id") or ""))
        if memory is None:
            from modules.llm.memory.models import Memory

            memory = Memory.fromDict(data)
        embeddingManager.refreshMemory(memory)

    def _handleMemoryDeleted(self, data: dict):
        embeddingManager = getattr(self.memoryManager, "memoryEmbeddingManager", None)
        if embeddingManager is None:
            return
        memoryId = str(data.get("memoryId") or data.get("memory_id") or "")
        if memoryId:
            embeddingManager.removeMemory(memoryId)

    def _handleReindexRequested(self):
        memoryManager = self.memoryManager
        embeddingManager = getattr(memoryManager, "memoryEmbeddingManager", None)
        if embeddingManager is None:
            return
        memories = memoryManager.store.queryMemories() if hasattr(memoryManager.store, "queryMemories") else []
        embeddingManager.reindexAll(memories)

    @staticmethod
    def _sessionId(data: dict) -> str:
        return str(data.get("sessionId") or data.get("session_id") or data.get("conversationId") or "default")
