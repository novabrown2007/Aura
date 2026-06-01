"""Email sending operations."""

from __future__ import annotations

from typing import Any
from email.utils import parseaddr

from modules.email.models import EmailDraft


class EmailSendManager:
    """Send emails after safety validation and provider routing."""

    def __init__(self, context=None, connectionManager=None, draftManager=None):
        self.context = context
        self.connectionManager = connectionManager
        self.draftManager = draftManager
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Send") if getattr(context, "logger", None) else None

    def sendEmail(self, accountId: str = "", draftId: str = "", to=None, cc=None, bcc=None, subject: str = "", body: str = "", attachments=None, metadata: dict[str, Any] | None = None):
        accountId = str(accountId or self._defaultAccountId())
        draft = self._resolveDraft(accountId, draftId, to=to, cc=cc, bcc=bcc, subject=subject, body=body, attachments=attachments, metadata=metadata)
        self._validateRecipients(draft)
        provider = self.connectionManager.getProvider(accountId) if self.connectionManager is not None else None
        if provider is None:
            raise RuntimeError("Email provider unavailable.")
        sent = provider.sendEmail(accountId, draft)
        self._emit("email.sent", sent)
        return sent

    def sendDraft(self, draftId: str):
        draft = self.draftManager.getDraft(draftId) if self.draftManager is not None else None
        if draft is None:
            raise KeyError(f"Unknown draft: {draftId}")
        return self.sendEmail(accountId=draft.accountId, draftId=draft.draftId, metadata=draft.metadata)

    def snapshot(self):
        return {"available": True}

    def _resolveDraft(self, accountId: str, draftId: str, **fields):
        if draftId and self.draftManager is not None:
            draft = self.draftManager.getDraft(draftId)
            if draft is None:
                raise KeyError(f"Unknown draft: {draftId}")
            return draft
        draft = EmailDraft(
            draftId=draftId or "",
            accountId=accountId,
            to=list(fields.get("to") or []),
            cc=list(fields.get("cc") or []),
            bcc=list(fields.get("bcc") or []),
            subject=str(fields.get("subject") or ""),
            body=str(fields.get("body") or ""),
            attachments=[dict(item) for item in (fields.get("attachments") or [])],
            metadata=dict(fields.get("metadata") or {}),
        )
        if self.draftManager is not None:
            draft = self.draftManager.saveDraft(draft)
        return draft

    def _defaultAccountId(self):
        accountManager = getattr(self.context, "emailAccountManager", None)
        if accountManager is None:
            return ""
        default = accountManager.getDefaultAccount()
        return default.accountId if default is not None else ""

    def _emit(self, name: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None

    @staticmethod
    def _validateRecipients(draft: EmailDraft):
        recipients = list(draft.to or [])
        if not recipients:
            raise ValueError("At least one recipient is required.")
        invalid = [recipient for recipient in recipients if not parseaddr(str(recipient))[1]]
        if invalid:
            raise ValueError(f"Invalid recipient address: {invalid[0]}")
