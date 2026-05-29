"""Clarification state coordination."""

from __future__ import annotations

from typing import Any

from core.conversation.conversationContext import ConversationContext


class ClarificationManager:
    """Track pending clarification flows without owning tool execution."""

    def __init__(self, context: ConversationContext):
        self.context = context

    def start(self, question: str, pendingIntent: dict[str, Any], missingField: str = ""):
        self.context.setClarification(question, pendingIntent, missingField)

    def complete(self):
        self.context.clearClarification()

    def hasPending(self) -> bool:
        return bool(self.context.state.pendingClarification.active)

    def snapshot(self) -> dict[str, Any]:
        return self.context.state.pendingClarification.asDict()

