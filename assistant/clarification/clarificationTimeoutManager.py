"""Clarification timeout handling."""

from __future__ import annotations

from time import time

from assistant.clarification.models import ClarificationState


class ClarificationTimeoutManager:
    """Expire stale clarification sessions safely."""

    def __init__(self, context=None, sessionManager=None, timeoutSeconds: int = 60):
        self.context = context
        self.sessionManager = sessionManager
        self.timeoutSeconds = int(timeoutSeconds or 60)
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild("Clarification.Timeout") if logger else None

    def expire(self):
        expired = []
        manager = self.sessionManager or getattr(self.context, "clarificationManager", None)
        if manager is None or not hasattr(manager, "listActiveSessions"):
            return expired
        now = time()
        for session in list(manager.listActiveSessions()):
            request = session.activeRequest.asDict() if hasattr(session.activeRequest, "asDict") else dict(session.activeRequest or {})
            timeoutAt = float(request.get("timeoutAt") or 0.0)
            if timeoutAt and now > timeoutAt:
                expired.append(manager.timeout(session.sessionId))
        return expired
