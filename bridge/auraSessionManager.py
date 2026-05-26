"""Session management for assistant-facing Aura protocol interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AuraSession:
    """One assistant session."""

    sessionId: str
    interface: str
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    createdAt: str = field(default_factory=_now)
    lastSeenAt: str = field(default_factory=_now)


class AuraSessionManager:
    """Track assistant sessions across interfaces and modalities."""

    def __init__(self, context=None):
        self.context = context
        self.sessions: dict[str, AuraSession] = {}
        self.activeSessionId: str = ""

    def createSession(self, interface: str, metadata: dict[str, Any] | None = None, sessionId: str | None = None) -> AuraSession:
        """Create or replace one session record."""

        session = AuraSession(
            sessionId=sessionId or f"{interface}-{uuid4().hex}",
            interface=str(interface or "unknown"),
            metadata=dict(metadata or {}),
        )
        self.sessions[session.sessionId] = session
        self.activeSessionId = session.sessionId
        return session

    def getSession(self, sessionId: str | None = None) -> AuraSession | None:
        """Return a known session."""

        if not sessionId:
            sessionId = self.activeSessionId
        return self.sessions.get(sessionId or "")

    def getActiveSession(self) -> AuraSession | None:
        """Return the current active session."""

        return self.getSession(self.activeSessionId)

    def setActiveSession(self, sessionId: str) -> AuraSession | None:
        """Mark one session active."""

        session = self.sessions.get(sessionId)
        if session is None:
            return None
        self.activeSessionId = sessionId
        session.active = True
        session.lastSeenAt = _now()
        return session

    def touchSession(self, sessionId: str | None = None, context: dict[str, Any] | None = None) -> AuraSession | None:
        """Update session liveness and merge any assistant context."""

        session = self.getSession(sessionId)
        if session is None:
            return None
        session.lastSeenAt = _now()
        if context:
            session.context.update(context)
        return session

    def syncContext(self, sessionId: str | None = None, context: dict[str, Any] | None = None) -> AuraSession | None:
        """Merge bridge context into a session record."""

        return self.touchSession(sessionId, context=context)

    def listSessions(self) -> list[AuraSession]:
        """Return known sessions in creation order."""

        return list(self.sessions.values())

    def buildContext(self, interface: str, sessionId: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a normalized context block for protocol messages."""

        session = self.getSession(sessionId)
        if session is None:
            session = self.createSession(interface=interface, sessionId=sessionId)
        payload = {
            "sessionId": session.sessionId,
            "interface": session.interface,
        }
        if extra:
            payload.update(extra)
        return payload

