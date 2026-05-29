"""Conversation continuity event names."""


class ConversationEvents:
    """Central event names emitted by the conversation system."""

    STARTED = "conversation.started"
    UPDATED = "conversation.updated"
    FOLLOWUP_DETECTED = "conversation.followup.detected"
    REFERENCE_RESOLVED = "conversation.reference.resolved"
    CONTEXT_EXPIRED = "conversation.context.expired"
    CLARIFICATION_STARTED = "conversation.clarification.started"
    CLARIFICATION_COMPLETED = "conversation.clarification.completed"

