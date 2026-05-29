"""Follow-up resolution facade."""

from __future__ import annotations

from core.conversation.conversationContext import ConversationContext
from core.conversation.models import FollowupRequest
from core.conversation.referenceResolver import ReferenceResolver
from core.conversation.resolution import IntentContinuationResolver


class FollowupResolver:
    """Resolve pronouns, implied entities, and contextual modifications."""

    def __init__(self):
        self.references = ReferenceResolver()
        self.continuations = IntentContinuationResolver()

    def resolve(self, text: str, context: ConversationContext) -> FollowupRequest:
        original = str(text or "")
        resolved, references = self.references.resolve(original, context)
        isFollowup = bool(references)
        if self.continuations.isContinuation(resolved, context):
            resolved = self.continuations.resolve(resolved, context)
            isFollowup = True
        topic = context.activeTopic()
        entity = context.activeEntity()
        return FollowupRequest(
            originalText=original,
            resolvedText=resolved,
            isFollowup=isFollowup,
            resolvedReferences=references,
            activeTopic=topic.name if topic else "",
            activeEntity=entity.name if entity else "",
        )

