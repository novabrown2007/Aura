"""Runtime context management for clarification flows."""

from __future__ import annotations

from assistant.clarification.models import ClarificationRequest


class ClarificationContextManager:
    """Build compact context snapshots for clarifications."""

    def __init__(self, context=None, conversationContext=None):
        self.context = context
        self.conversationContext = conversationContext
        self.lastContext = {}
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Context") if logger else None

    def buildContext(self, userInput: str = "", sourceIntent: dict | None = None, request: ClarificationRequest | None = None) -> dict:
        conversation = {}
        conversationManager = getattr(self.context, "conversationManager", None)
        if conversationManager is not None and hasattr(conversationManager, "snapshot"):
            try:
                conversation = conversationManager.snapshot()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Clarification conversation snapshot failed: {error}")
        elif self.conversationContext is not None and hasattr(self.conversationContext, "snapshot"):
            try:
                conversation = self.conversationContext.snapshot()
            except Exception:
                conversation = {}

        execution = {}
        executionManager = getattr(self.context, "executionManager", None)
        if executionManager is not None and hasattr(executionManager, "snapshot"):
            try:
                execution = executionManager.snapshot()
            except Exception as error:
                if self.logger:
                    self.logger.warning(f"Clarification execution snapshot failed: {error}")

        memory = {}
        memoryManager = getattr(self.context, "memoryManager", None)
        if memoryManager is not None and hasattr(memoryManager, "getMemory"):
            try:
                memory = memoryManager.getMemory() or {}
            except Exception:
                memory = {}

        clarification = request.asDict() if hasattr(request, "asDict") else dict(request or {})
        self.lastContext = {
            "conversation": conversation,
            "execution": execution,
            "memory": memory,
            "clarification": clarification,
            "sourceIntent": dict(sourceIntent or {}),
            "userInput": str(userInput or ""),
        }
        return self.lastContext

    def snapshot(self) -> dict:
        return dict(self.lastContext or {})
