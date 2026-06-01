"""Session management for pending clarifications."""

from __future__ import annotations

from time import time
from typing import Any

from assistant.clarification.models import ClarificationRequest, ClarificationSession, ClarificationState
from assistant.clarification.storage import ClarificationSessionStore


class ClarificationSessionManager:
    """Track, resolve, and expire clarification sessions."""

    def __init__(self, context=None, store: ClarificationSessionStore | None = None):
        self.context = context
        self.store = store or ClarificationSessionStore()
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Sessions") if logger else None
        self.activeSessionIdByConversation: dict[str, str] = {}

    def createSession(self, request: ClarificationRequest, pendingIntent: dict[str, Any] | None = None, pendingAction: dict[str, Any] | None = None, conversationContext: dict[str, Any] | None = None) -> ClarificationSession:
        conversationContext = dict(conversationContext or {})
        conversationContext.setdefault("conversationId", request.conversationId)
        session = ClarificationSession(
            activeRequest=request,
            conversationContext=conversationContext,
            pendingIntent=dict(pendingIntent or request.sourceIntent or {}),
            pendingAction=dict(pendingAction or {}),
            state=ClarificationState.WAITING_FOR_RESPONSE,
            metadata=dict(request.metadata or {}),
        )
        self.store.upsert(session)
        self.activeSessionIdByConversation[str(request.conversationId or "default")] = session.sessionId
        self._emit("clarification.requested", session.asDict())
        return session

    def getSession(self, sessionId: str) -> ClarificationSession | None:
        return self.store.get(sessionId)

    def getActiveSession(self, conversationId: str = "default") -> ClarificationSession | None:
        sessionId = self.activeSessionIdByConversation.get(str(conversationId or "default"))
        if sessionId:
            session = self.store.get(sessionId)
            if session is not None:
                return session
        return self.store.findByConversation(conversationId)

    def listActiveSessions(self) -> list[ClarificationSession]:
        return [session for session in self.store.all() if self._isActive(session)]

    def resolve(self, sessionId: str, userInput: str, resolver) -> dict[str, Any]:
        session = self.store.get(sessionId)
        if session is None:
            return {"resolved": False, "reason": "Missing clarification session."}
        session.attempts += 1
        session.touch()
        result = resolver.resolve(session, userInput)
        if result.get("resolved"):
            session.state = ClarificationState.RESOLVED
            session.touch()
            self.store.upsert(session)
            self.activeSessionIdByConversation.pop(self._conversationId(session), None)
            self._emit("clarification.resolved", {**session.asDict(), "resolution": result})
            return result
        if session.attempts >= int(self._config("clarification.maxClarificationAttempts", 3)):
            return self.cancel(session.sessionId, reason=result.get("reason") or "Too many attempts.")
        self.store.upsert(session)
        return result

    def cancel(self, sessionId: str, reason: str = "Cancelled") -> dict[str, Any]:
        session = self.store.get(sessionId)
        if session is None:
            return {"resolved": False, "reason": reason}
        session.state = ClarificationState.CANCELLED
        session.touch()
        self.store.upsert(session)
        self.activeSessionIdByConversation.pop(self._conversationId(session), None)
        payload = session.asDict()
        payload["reason"] = reason
        self._emit("clarification.cancelled", payload)
        return {"resolved": False, "cancelled": True, "reason": reason}

    def timeout(self, sessionId: str) -> dict[str, Any]:
        session = self.store.get(sessionId)
        if session is None:
            return {"resolved": False, "reason": "Missing clarification session."}
        session.state = ClarificationState.TIMED_OUT
        session.touch()
        self.store.upsert(session)
        self.activeSessionIdByConversation.pop(self._conversationId(session), None)
        payload = session.asDict()
        self._emit("clarification.timed_out", payload)
        return {"resolved": False, "timedOut": True, "session": payload}

    def complete(self, sessionId: str):
        self.store.delete(sessionId)

    def snapshot(self) -> dict[str, Any]:
        sessions = [session.asDict() for session in self.store.all()]
        return {
            "available": True,
            "activeCount": len(self.listActiveSessions()),
            "sessions": sessions,
            "activeSessions": [session for session in sessions if session.get("state") == ClarificationState.WAITING_FOR_RESPONSE.value],
        }

    def _conversationId(self, session: ClarificationSession) -> str:
        request = session.activeRequest.asDict() if hasattr(session.activeRequest, "asDict") else dict(session.activeRequest or {})
        return str(request.get("conversationId") or session.conversationContext.get("conversationId") or "default")

    @staticmethod
    def _isActive(session: ClarificationSession) -> bool:
        return session.state == ClarificationState.WAITING_FOR_RESPONSE

    def _emit(self, eventName: str, payload: dict[str, Any]):
        eventManager = getattr(self.context, "eventManager", None)
        if eventManager is None:
            return
        try:
            eventManager.emit(eventName, payload)
        except Exception as error:
            if self.logger:
                self.logger.warning(f"Clarification event emission failed for {eventName}: {error}")

    @staticmethod
    def _configBool(value, default: bool = True) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _config(self, key: str, default=None):
        config = getattr(self.context, "config", None)
        if config is None or not hasattr(config, "get"):
            return default
        return config.get(key, default)
