"""Persistence for clarification sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from assistant.clarification.models import ClarificationSession, ClarificationState


class ClarificationSessionStore:
    """Persist clarification sessions in memory or JSON on disk."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.sessions: dict[str, ClarificationSession] = {}
        self._load()

    def upsert(self, session: ClarificationSession):
        self.sessions[session.sessionId] = session
        self._save()
        return session

    def get(self, sessionId: str) -> ClarificationSession | None:
        return self.sessions.get(str(sessionId or ""))

    def findByConversation(self, conversationId: str) -> ClarificationSession | None:
        for session in self.sessions.values():
            request = session.activeRequest.asDict() if hasattr(session.activeRequest, "asDict") else dict(session.activeRequest or {})
            if str(request.get("conversationId") or session.conversationContext.get("conversationId") or "") == str(conversationId or ""):
                return session
        return None

    def delete(self, sessionId: str):
        self.sessions.pop(str(sessionId or ""), None)
        self._save()

    def all(self) -> list[ClarificationSession]:
        return list(self.sessions.values())

    def clear(self):
        self.sessions.clear()
        self._save()

    def _load(self):
        if self.path is None or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            for sessionId, payload in data.items():
                if not isinstance(payload, dict):
                    continue
                session = ClarificationSession(
                    sessionId=sessionId,
                    activeRequest=payload.get("activeRequest", {}),
                    conversationContext=dict(payload.get("conversationContext") or {}),
                    pendingIntent=dict(payload.get("pendingIntent") or {}),
                    pendingAction=dict(payload.get("pendingAction") or {}),
                    state=self._stateFromPayload(payload.get("state")),
                    createdAt=float(payload.get("createdAt") or 0.0),
                    updatedAt=float(payload.get("updatedAt") or 0.0),
                    attempts=int(payload.get("attempts") or 0),
                    metadata=dict(payload.get("metadata") or {}),
                )
                self.sessions[sessionId] = session
        except Exception:
            self.sessions = {}

    def _save(self):
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {sessionId: session.asDict() for sessionId, session in self.sessions.items()}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _stateFromPayload(value) -> ClarificationState:
        try:
            if isinstance(value, ClarificationState):
                return value
            return ClarificationState(str(value or ClarificationState.PENDING.value).split(".")[-1])
        except Exception:
            return ClarificationState.PENDING
