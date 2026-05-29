"""Short-term conversational context storage."""

from __future__ import annotations

from time import time
from typing import Any

from core.conversation.models import ActiveEntity, ActiveTopic, ClarificationState, ConversationState, FollowupRequest


class ConversationContext:
    """Own the current short-term conversational state."""

    def __init__(self, timeoutSeconds: int = 300, sessionId: str = "default"):
        self.timeoutSeconds = int(timeoutSeconds or 300)
        now = time()
        self.state = ConversationState(
            sessionId=sessionId,
            createdAt=now,
            updatedAt=now,
            expiresAt=now + self.timeoutSeconds,
        )

    def isExpired(self) -> bool:
        return time() > float(self.state.expiresAt or 0.0)

    def touch(self):
        now = time()
        self.state.updatedAt = now
        self.state.expiresAt = now + self.timeoutSeconds

    def reset(self):
        sessionId = self.state.sessionId
        now = time()
        self.state = ConversationState(
            sessionId=sessionId,
            createdAt=now,
            updatedAt=now,
            expiresAt=now + self.timeoutSeconds,
        )

    def addEntity(self, entity: ActiveEntity):
        self.touch()
        entity.updatedAt = time()
        if not entity.createdAt:
            entity.createdAt = entity.updatedAt
        self.state.activeEntities = [
            existing for existing in self.state.activeEntities
            if existing.name.lower() != entity.name.lower()
        ]
        self.state.activeEntities.insert(0, entity)
        self.state.activeEntities = self.state.activeEntities[:10]

    def addTopic(self, topic: ActiveTopic):
        self.touch()
        topic.updatedAt = time()
        if not topic.createdAt:
            topic.createdAt = topic.updatedAt
        self.state.activeTopics = [
            existing for existing in self.state.activeTopics
            if existing.name.lower() != topic.name.lower()
        ]
        self.state.activeTopics.insert(0, topic)
        self.state.activeTopics = self.state.activeTopics[:8]

    def addAction(self, action: dict[str, Any]):
        self.touch()
        action = dict(action or {})
        action.setdefault("timestamp", time())
        self.state.activeActions.insert(0, action)
        self.state.activeActions = self.state.activeActions[:10]
        if action.get("intent"):
            self.state.recentIntents.insert(0, action)
            self.state.recentIntents = self.state.recentIntents[:10]

    def addFollowup(self, request: FollowupRequest):
        self.touch()
        self.state.followupChains.append(request)
        self.state.followupChains = self.state.followupChains[-12:]

    def addTimelineEvent(self, eventType: str, data: dict[str, Any] | None = None):
        self.touch()
        self.state.timeline.append({"type": eventType, "timestamp": time(), "data": data or {}})
        self.state.timeline = self.state.timeline[-50:]

    def setClarification(self, question: str, pendingIntent: dict[str, Any], missingField: str = ""):
        now = time()
        self.state.pendingClarification = ClarificationState(
            active=True,
            question=question,
            pendingIntent=dict(pendingIntent or {}),
            missingField=missingField,
            createdAt=now,
            updatedAt=now,
        )
        self.touch()

    def clearClarification(self):
        self.state.pendingClarification = ClarificationState()
        self.touch()

    def activeEntity(self) -> ActiveEntity | None:
        return self.state.activeEntities[0] if self.state.activeEntities else None

    def activeTopic(self) -> ActiveTopic | None:
        return self.state.activeTopics[0] if self.state.activeTopics else None

    def activeAction(self) -> dict[str, Any]:
        return dict(self.state.activeActions[0]) if self.state.activeActions else {}

    def resolutionData(self) -> dict[str, Any]:
        entity = self.activeEntity()
        topic = self.activeTopic()
        return {
            "activeEntity": entity.asDict() if entity else {},
            "activeTopic": topic.asDict() if topic else {},
            "activeAction": self.activeAction(),
            "pendingClarification": self.state.pendingClarification.asDict(),
        }

    def snapshot(self) -> dict[str, Any]:
        return self.state.asDict()

