"""Session lifecycle debugging for assistant simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utcNow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SessionRecord:
    """One active or historical assistant session."""

    sessionId: str
    interface: str
    state: str = "active"
    createdAt: str = field(default_factory=_utcNow)
    updatedAt: str = field(default_factory=_utcNow)
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionDebugger:
    """Track session lifecycle and interface state."""

    def __init__(self, context=None):
        self.context = context
        self.logger = context.logger.getChild("Testing.Session") if context and getattr(context, "logger", None) else None
        self.sessions: dict[str, SessionRecord] = {}

    def createSession(self, interface: str = "desktop", sessionId: str | None = None, metadata: dict[str, Any] | None = None):
        """Create or refresh one session."""

        sessionId = str(sessionId or uuid4().hex)
        record = self.sessions.get(sessionId) or SessionRecord(sessionId=sessionId, interface=str(interface or "desktop"))
        record.interface = str(interface or record.interface)
        record.state = "active"
        record.updatedAt = _utcNow()
        if metadata:
            record.metadata.update(metadata)
        self.sessions[sessionId] = record
        if self.logger:
            self.logger.debug(f"Session created: {sessionId} ({record.interface})")
        return record

    def updateSession(self, sessionId: str, **updates):
        """Update one session record."""

        record = self.sessions.get(str(sessionId))
        if record is None:
            record = self.createSession(sessionId=sessionId, interface=str(updates.get("interface") or "desktop"))
        if "interface" in updates and updates["interface"]:
            record.interface = str(updates["interface"])
        if "state" in updates and updates["state"]:
            record.state = str(updates["state"])
        if "metadata" in updates and isinstance(updates["metadata"], dict):
            record.metadata.update(updates["metadata"])
        record.updatedAt = _utcNow()
        return record

    def closeSession(self, sessionId: str):
        """Mark a session closed."""

        record = self.sessions.get(str(sessionId))
        if record is None:
            return None
        record.state = "closed"
        record.updatedAt = _utcNow()
        return record

    def listActiveSessions(self) -> list[dict[str, Any]]:
        """Return active sessions as dictionaries."""

        return [
            {
                "sessionId": record.sessionId,
                "interface": record.interface,
                "state": record.state,
                "createdAt": record.createdAt,
                "updatedAt": record.updatedAt,
                "metadata": dict(record.metadata),
            }
            for record in self.sessions.values()
        ]

    def snapshot(self) -> dict[str, Any]:
        """Return a compact session snapshot."""

        return {"activeSessions": self.listActiveSessions()}

    def getSession(self, sessionId: str):
        """Return a single session record by id."""

        return self.sessions.get(str(sessionId))

    def getActiveSessions(self) -> list[dict[str, Any]]:
        """Return active session dictionaries."""

        return [item for item in self.listActiveSessions() if item.get("state") == "active"]
