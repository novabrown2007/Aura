"""High-level clarification coordinator for Aura."""

from __future__ import annotations

from assistant.clarification.clarificationContextManager import ClarificationContextManager
from assistant.clarification.clarificationEngine import ClarificationEngine
from assistant.clarification.clarificationResolver import ClarificationResolver
from assistant.clarification.clarificationResponseBuilder import ClarificationResponseBuilder
from assistant.clarification.clarificationSessionManager import ClarificationSessionManager
from assistant.clarification.clarificationTimeoutManager import ClarificationTimeoutManager
from assistant.clarification.handlers.clarificationEventHandler import ClarificationEventHandler
from assistant.clarification.models import ClarificationOption, ClarificationRequest, ClarificationState, ClarificationType
from assistant.clarification.storage import ClarificationSessionStore


class ClarificationManager:
    """Coordinate ambiguity detection, clarification requests, and resolution."""

    def __init__(self, context=None, conversationContext=None, store: ClarificationSessionStore | None = None):
        self.context = context
        self.conversationContext = conversationContext
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification") if logger else None
        self.contextManager = ClarificationContextManager(context, conversationContext)
        self.engine = ClarificationEngine(context)
        self.resolver = ClarificationResolver(context)
        self.sessionManager = ClarificationSessionManager(context, store=store)
        self.timeoutManager = ClarificationTimeoutManager(context, self.sessionManager, timeoutSeconds=self._config("clarification.clarificationTimeoutSeconds", 60))
        self.responseBuilder = ClarificationResponseBuilder(context, self.contextManager)
        self.eventHandler = ClarificationEventHandler(context, self)
        self.lastRequest: ClarificationRequest | None = None
        self.lastResponse = None
        self.lastSessionId: str = ""
        if self.context is not None:
            self.context.clarificationManager = self
        self.eventHandler.subscribe()

    def start(self, question: str, pendingIntent: dict, missingField: str = "", conversationId: str = "default"):
        """Compatibility entrypoint used by the conversation manager."""

        sourceIntent = dict(pendingIntent or {})
        sourceIntent.setdefault("intent", str(sourceIntent.get("intent") or ""))
        sourceIntent.setdefault("arguments", dict(sourceIntent.get("arguments") or {}))
        request = ClarificationRequest(
            conversationId=str(conversationId or "default"),
            sourceIntent=sourceIntent,
            clarificationType=ClarificationType.MISSING_PARAMETER if missingField else ClarificationType.LOW_CONFIDENCE,
            question=str(question or ""),
            requiredParameter=str(missingField or ""),
            metadata={"missingField": missingField} if missingField else {},
        )
        return self.requestClarification(request, pendingIntent=sourceIntent)

    def requestClarification(
        self,
        request_or_intent,
        clarificationType: ClarificationType | str | None = None,
        question: str = "",
        options: list[ClarificationOption] | None = None,
        requiredParameter: str = "",
        conversationId: str = "default",
        pendingIntent: dict | None = None,
        pendingAction: dict | None = None,
        metadata: dict | None = None,
    ):
        """Create and store one clarification session."""

        if isinstance(request_or_intent, ClarificationRequest):
            request = request_or_intent
        else:
            sourceIntent = dict(request_or_intent or {})
            ambiguity = self.engine.detect(sourceIntent, candidates=options)
            if clarificationType is not None:
                if isinstance(clarificationType, ClarificationType):
                    ambiguity.clarificationType = clarificationType
                else:
                    ambiguity.clarificationType = ClarificationType(str(clarificationType).split(".")[-1])
            if question:
                ambiguity.question = question
            if options is not None:
                ambiguity.options = list(options)
            if requiredParameter:
                ambiguity.requiredParameter = requiredParameter
            request = self.engine.createRequest(
                sourceIntent,
                ambiguity=ambiguity,
                conversationId=conversationId,
                requiredParameter=requiredParameter,
                question=question,
                options=options,
                metadata=metadata,
            )

        conversationContext = self.contextManager.buildContext(
            request.question,
            sourceIntent=request.sourceIntent,
            request=request,
        )
        session = self.sessionManager.createSession(
            request,
            pendingIntent=pendingIntent or request.sourceIntent,
            pendingAction=pendingAction,
            conversationContext=conversationContext,
        )
        self._syncConversationClarification(request)
        self.lastRequest = request
        self.lastSessionId = session.sessionId
        self.lastResponse = self.responseBuilder.buildRequestResponse(request, conversationContext=conversationContext)
        return {
            "request": request,
            "session": session,
            "response": self.lastResponse,
            "payload": self.lastResponse.asDict(),
        }

    def resolveResponse(self, userInput: str, conversationId: str = "default", sessionId: str | None = None):
        """Resolve a user reply against the active clarification session."""

        self.timeoutManager.expire()
        session = None
        if sessionId:
            session = self.sessionManager.getSession(sessionId)
        if session is None:
            session = self.sessionManager.getActiveSession(conversationId)
        if session is None:
            return {"resolved": False, "reason": "No active clarification."}

        result = self.sessionManager.resolve(session.sessionId, userInput, self.resolver)
        if not result.get("resolved"):
            return result

        payload = {
            "resolved": True,
            "session": session.asDict() if hasattr(session, "asDict") else {},
            "request": session.activeRequest.asDict() if hasattr(session.activeRequest, "asDict") else dict(session.activeRequest or {}),
            "result": result,
        }
        self.lastResponse = self.responseBuilder.buildResolvedResponse(session.activeRequest, result)
        return payload

    def complete(self, sessionId: str | None = None, conversationId: str = "default"):
        """Mark a clarification as complete and clear it from storage."""

        session = None
        if sessionId:
            session = self.sessionManager.getSession(sessionId)
        if session is None:
            session = self.sessionManager.getActiveSession(conversationId)
        if session is None:
            return {"completed": False}
        self.sessionManager.complete(session.sessionId)
        self._clearConversationClarification()
        self.lastRequest = None
        self.lastSessionId = ""
        return {"completed": True, "sessionId": session.sessionId}

    def cancel(self, sessionId: str | None = None, conversationId: str = "default", reason: str = "Cancelled"):
        session = None
        if sessionId:
            session = self.sessionManager.getSession(sessionId)
        if session is None:
            session = self.sessionManager.getActiveSession(conversationId)
        if session is None:
            return {"cancelled": False, "reason": reason}
        result = self.sessionManager.cancel(session.sessionId, reason=reason)
        self._clearConversationClarification()
        return result

    def timeout(self, sessionId: str | None = None, conversationId: str = "default"):
        session = None
        if sessionId:
            session = self.sessionManager.getSession(sessionId)
        if session is None:
            session = self.sessionManager.getActiveSession(conversationId)
        if session is None:
            return {"timedOut": False}
        result = self.sessionManager.timeout(session.sessionId)
        self._clearConversationClarification()
        return result

    def hasPending(self, conversationId: str = "default") -> bool:
        return self.sessionManager.getActiveSession(conversationId) is not None

    def getPending(self, conversationId: str = "default"):
        session = self.sessionManager.getActiveSession(conversationId)
        return session.asDict() if session is not None and hasattr(session, "asDict") else {}

    def listActiveSessions(self):
        return self.sessionManager.listActiveSessions()

    def snapshot(self) -> dict:
        snapshot = self.sessionManager.snapshot()
        snapshot["lastRequest"] = self.lastRequest.asDict() if self.lastRequest is not None else {}
        snapshot["lastResponse"] = self.lastResponse.asDict() if self.lastResponse is not None and hasattr(self.lastResponse, "asDict") else {}
        snapshot["enabled"] = bool(self._config("clarification.clarificationEnabled", True))
        snapshot["timeoutSeconds"] = int(self._config("clarification.clarificationTimeoutSeconds", 60))
        snapshot["lastSessionId"] = str(self.lastSessionId or "")
        snapshot["available"] = True
        return snapshot

    def shutdown(self):
        self.eventHandler.unsubscribe()

    def _config(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)

    def _syncConversationClarification(self, request: ClarificationRequest):
        conversationManager = getattr(self.context, "conversationManager", None)
        conversationContext = getattr(conversationManager, "context", None) if conversationManager is not None else self.conversationContext
        if conversationContext is None or not hasattr(conversationContext, "setClarification"):
            return
        try:
            conversationContext.setClarification(request.question, request.sourceIntent, request.requiredParameter)
        except Exception as error:
            if self.logger:
                self.logger.debug(f"Clarification conversation sync failed: {error}")

    def _clearConversationClarification(self):
        conversationManager = getattr(self.context, "conversationManager", None)
        conversationContext = getattr(conversationManager, "context", None) if conversationManager is not None else self.conversationContext
        if conversationContext is None or not hasattr(conversationContext, "clearClarification"):
            return
        try:
            conversationContext.clearClarification()
        except Exception as error:
            if self.logger:
                self.logger.debug(f"Clarification conversation clear failed: {error}")
