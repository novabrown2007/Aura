"""Aura conversational continuity coordinator."""

from __future__ import annotations

from typing import Any

from assistant.clarification import ClarificationManager
from core.conversation.conversationContext import ConversationContext
from core.conversation.conversationTracker import ConversationTracker
from core.conversation.events import ConversationEvents
from core.conversation.followupResolver import FollowupResolver
from core.conversation.tracking import ActionTracker, EntityTracker, TopicTracker


class ConversationManager:
    """Coordinate short-term conversational continuity for Aura."""

    def __init__(self, context=None):
        self.runtimeContext = context
        self.logger = None
        self.timeoutSeconds = 300
        if context is not None:
            config = getattr(context, "config", None)
            self.timeoutSeconds = int(self._config(config, "conversation.conversationTimeoutSeconds", self._config(config, "conversationTimeoutSeconds", 300)))
            logger = getattr(context, "logger", None)
            self.logger = logger.getChild("Conversation") if logger else None
        self.context = ConversationContext(timeoutSeconds=self.timeoutSeconds)
        self.tracker = ConversationTracker(self.context)
        self.followups = FollowupResolver()
        self.clarifications = ClarificationManager(self.runtimeContext, conversationContext=self.context)
        self.actions = ActionTracker()
        self.entities = EntityTracker()
        self.topics = TopicTracker()
        if context is not None:
            context.conversationManager = self
            context.clarificationManager = self.clarifications

    def preprocessInput(self, userInput: str, sessionId: str = "default") -> str:
        """Resolve references before the provider or intent pipeline sees text."""

        self._expireIfNeeded()
        if self.context.state.sessionId != sessionId:
            self.context.state.sessionId = sessionId
        if not self.context.state.timeline:
            self._emit(ConversationEvents.STARTED, {"sessionId": sessionId})

        request = self.followups.resolve(userInput, self.context)
        if request.isFollowup:
            self.context.addFollowup(request)
            self._emit(ConversationEvents.FOLLOWUP_DETECTED, request.asDict())
            if request.resolvedReferences:
                self._emit(ConversationEvents.REFERENCE_RESOLVED, request.asDict())
            if self.logger:
                self.logger.info(f"Resolved follow-up: {request.originalText} -> {request.resolvedText}")

        self.tracker.trackResolvedTurn(request.originalText, request.resolvedText)
        self._emit(ConversationEvents.UPDATED, self.snapshot())
        return request.resolvedText

    def recordAction(self, intent: str, arguments: dict[str, Any], result: dict[str, Any] | None = None):
        """Record an executed action as conversational context."""

        self._expireIfNeeded()
        action = self.actions.fromIntent(intent, arguments, result)
        self.context.addAction(action)
        topic = self.topics.fromIntent(intent)
        if topic is not None:
            self.context.addTopic(topic)
        for entity in self.entities.fromAction(intent, arguments):
            self.context.addEntity(entity)
        self.context.addTimelineEvent("action", action)
        self._emit(ConversationEvents.UPDATED, self.snapshot())
        if self.logger:
            self.logger.info(f"Tracked conversational action: {intent}")

    def startClarification(self, question: str, pendingIntent: dict[str, Any], missingField: str = ""):
        self.context.setClarification(question, pendingIntent, missingField)
        result = self.clarifications.start(question, pendingIntent, missingField, conversationId=self.context.state.sessionId)
        session = result.get("session") if isinstance(result, dict) else None
        payload = session.asDict() if hasattr(session, "asDict") else (session if isinstance(session, dict) else self.context.state.pendingClarification.asDict())
        self._emit(ConversationEvents.CLARIFICATION_STARTED, payload)
        return result

    def completeClarification(self):
        details = self.context.state.pendingClarification.asDict()
        if not details.get("active"):
            lastRequest = getattr(self.clarifications, "lastRequest", None)
            if lastRequest is not None and hasattr(lastRequest, "asDict"):
                details = lastRequest.asDict()
        active = self.clarifications.getPending(self.context.state.sessionId)
        sessionId = str(active.get("sessionId") or "")
        if not sessionId:
            sessionId = str(getattr(self.clarifications, "lastSessionId", "") or "")
        if sessionId:
            self.clarifications.complete(sessionId)
        self.context.clearClarification()
        self._emit(ConversationEvents.CLARIFICATION_COMPLETED, details)

    def reset(self, reason: str = "manual"):
        self.context.reset()
        self._emit(ConversationEvents.CONTEXT_EXPIRED, {"reason": reason})

    def snapshot(self) -> dict[str, Any]:
        data = self.context.snapshot()
        activeTopic = self.context.activeTopic()
        activeEntity = self.context.activeEntity()
        data["activeTopic"] = activeTopic.asDict() if activeTopic else {}
        data["activeEntity"] = activeEntity.asDict() if activeEntity else {}
        data["followupChainLength"] = len(self.context.state.followupChains)
        data["clarification"] = self.clarifications.snapshot()
        return data

    def _expireIfNeeded(self):
        if not self.context.isExpired():
            return
        self.context.reset()
        self._emit(ConversationEvents.CONTEXT_EXPIRED, {"reason": "timeout", "timeoutSeconds": self.timeoutSeconds})
        if self.logger:
            self.logger.info("Conversation context expired.")

    def _emit(self, eventName: str, data: dict[str, Any]):
        eventManager = getattr(self.runtimeContext, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, data)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Conversation event emission failed: {error}")

    @staticmethod
    def _config(config, key: str, default=None):
        if config is None:
            return default
        return config.get(key, default)
