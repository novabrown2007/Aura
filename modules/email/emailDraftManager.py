"""Email draft lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from modules.email.models import EmailDraft


class EmailDraftManager:
    """Create, edit, and store drafts."""

    def __init__(self, context=None, store=None):
        self.context = context
        self.store = store
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Drafts") if getattr(context, "logger", None) else None
        self.drafts: dict[str, EmailDraft] = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self._loadPersistedDrafts()
        return self

    def createDraft(self, accountId: str, **fields):
        draft = EmailDraft.fromDict(fields)
        draft.accountId = str(accountId or draft.accountId or self._defaultAccountId())
        draft.draftId = draft.draftId or self._newId("draft")
        now = self._now()
        draft.createdAt = draft.createdAt or now
        draft.updatedAt = now
        self.drafts[draft.draftId] = draft
        self._persist(draft)
        self._emit("email.draft.created", draft.asDict())
        return draft

    def updateDraft(self, draftId: str, **fields):
        draft = self.drafts.get(str(draftId))
        if draft is None:
            return None
        for key, value in fields.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        draft.updatedAt = self._now()
        self._persist(draft)
        self._emit("email.draft.updated", draft.asDict())
        return draft

    def saveDraft(self, draft: EmailDraft):
        self.drafts[draft.draftId] = draft
        draft.updatedAt = self._now()
        self._persist(draft)
        return draft

    def getDraft(self, draftId: str):
        return self.drafts.get(str(draftId))

    def listDrafts(self, accountId: str | None = None):
        drafts = list(self.drafts.values())
        if accountId is not None:
            drafts = [draft for draft in drafts if draft.accountId == str(accountId)]
        return [draft.asDict() for draft in sorted(drafts, key=lambda item: item.updatedAt or item.createdAt, reverse=True)]

    def deleteDraft(self, draftId: str):
        draft = self.drafts.pop(str(draftId), None)
        return draft.asDict() if draft is not None else None

    def snapshot(self):
        return {"available": True, "count": len(self.drafts)}

    def _loadPersistedDrafts(self):
        if self.store is None:
            return
        for row in self.store.listDrafts():
            draft = EmailDraft.fromDict(row)
            if draft.draftId:
                self.drafts[draft.draftId] = draft

    def _persist(self, draft: EmailDraft):
        if self.store is not None:
            self.store.upsertDraft(draft.asDict())

    def _emit(self, name: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None

    def _defaultAccountId(self):
        accountManager = getattr(self.context, "emailAccountManager", None)
        if accountManager is None:
            return ""
        default = accountManager.getDefaultAccount()
        return default.accountId if default is not None else ""

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _newId(prefix: str):
        from uuid import uuid4

        return f"{prefix}-{uuid4().hex[:12]}"
