"""Conversation interruption handler."""

from __future__ import annotations


class ConversationInterruptionHandler:
    """Clear pending conversational state and clarification flows."""

    systemName = "conversation"

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Interruption.Conversation") if logger else None

    def cancel(self, interruptionContext) -> list[str]:
        """Reset interruption-sensitive conversation state."""

        cancelled = []
        config = getattr(self.context, "config", None)
        clearState = config.get("interruptions.interruptionClearConversationState", True) if config else True
        if not clearState:
            return cancelled

        for name in ("interpreter", "intentRouter", "llm"):
            target = getattr(self.context, name, None)
            if target is None:
                continue
            try:
                if hasattr(target, "cancelPending"):
                    target.cancelPending()
                    cancelled.append(name)
                elif hasattr(target, "resetConversationState"):
                    target.resetConversationState()
                    cancelled.append(name)
            except Exception as error:
                interruptionContext.markFailed(name, str(error))
        return cancelled

