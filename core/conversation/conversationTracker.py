"""Conversation flow tracking."""

from __future__ import annotations

from core.conversation.conversationContext import ConversationContext
from core.conversation.tracking import EntityTracker, TopicTracker


class ConversationTracker:
    """Track user turns, topics, entities, and timeline transitions."""

    def __init__(self, context: ConversationContext):
        self.context = context
        self.entities = EntityTracker()
        self.topics = TopicTracker()

    def trackUserTurn(self, text: str):
        topic = self.topics.extract(text)
        if topic is not None:
            self.context.addTopic(topic)
        activeTopic = self.context.activeTopic()
        for entity in self.entities.extract(text, topic=activeTopic.name if activeTopic else ""):
            self.context.addEntity(entity)
        self.context.addTimelineEvent("user", {"text": text})

    def trackResolvedTurn(self, original: str, resolved: str):
        if original != resolved:
            self.context.addTimelineEvent("resolved", {"original": original, "resolved": resolved})
        self.trackUserTurn(resolved)

