"""Reference resolver facade."""

from __future__ import annotations

from core.conversation.conversationContext import ConversationContext
from core.conversation.resolution import PronounResolver


class ReferenceResolver:
    """Coordinate deterministic conversational reference resolution."""

    def __init__(self):
        self.pronouns = PronounResolver()

    def resolve(self, text: str, context: ConversationContext) -> tuple[str, dict[str, str]]:
        return self.pronouns.resolve(text, context)

    def hasReference(self, text: str) -> bool:
        return self.pronouns.hasPronoun(text)

