"""Conversation state model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.conversation.models.activeEntity import ActiveEntity
from core.conversation.models.activeTopic import ActiveTopic
from core.conversation.models.clarificationState import ClarificationState
from core.conversation.models.followupRequest import FollowupRequest


@dataclass
class ConversationState:
    """Short-term conversational continuity state."""

    sessionId: str = "default"
    activeEntities: list[ActiveEntity] = field(default_factory=list)
    activeTopics: list[ActiveTopic] = field(default_factory=list)
    activeActions: list[dict[str, Any]] = field(default_factory=list)
    recentIntents: list[dict[str, Any]] = field(default_factory=list)
    pendingClarification: ClarificationState = field(default_factory=ClarificationState)
    followupChains: list[FollowupRequest] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    createdAt: float = 0.0
    updatedAt: float = 0.0
    expiresAt: float = 0.0

    def asDict(self) -> dict[str, Any]:
        return {
            "sessionId": self.sessionId,
            "activeEntities": [entity.asDict() for entity in self.activeEntities],
            "activeTopics": [topic.asDict() for topic in self.activeTopics],
            "activeActions": list(self.activeActions),
            "recentIntents": list(self.recentIntents),
            "pendingClarification": self.pendingClarification.asDict(),
            "followupChains": [request.asDict() for request in self.followupChains],
            "timeline": list(self.timeline),
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
            "expiresAt": self.expiresAt,
        }

