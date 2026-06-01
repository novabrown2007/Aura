"""Scheduled email support."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from modules.email.models import EmailDraft, ScheduledEmail


class EmailScheduleManager:
    """Track scheduled email sends and execute them on schedule ticks."""

    def __init__(self, context=None, sendManager=None, store=None):
        self.context = context
        self.sendManager = sendManager
        self.store = store
        self.logger = getattr(getattr(context, "logger", None), "getChild", lambda *_: None)("Email.Schedule") if getattr(context, "logger", None) else None
        self.scheduled: dict[str, ScheduledEmail] = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        self._loadPersisted()
        return self

    def scheduleEmail(self, accountId: str = "", draftId: str = "", sendAt: str = "", **fields):
        draft = self._resolveDraft(accountId, draftId, fields)
        scheduled = ScheduledEmail(
            scheduledEmailId=self._newId("scheduled-email"),
            draft=draft,
            sendAt=str(sendAt or ""),
            state="PENDING",
            createdAt=self._now(),
            metadata={"scheduleItemId": self._scheduleItemIdFor(draft, sendAt), **dict(fields.get("metadata") or {})},
        )
        self.scheduled[scheduled.scheduledEmailId] = scheduled
        self._persist(scheduled)
        self._createScheduleItem(scheduled)
        self._emit("email.scheduled", scheduled.asDict())
        return scheduled

    def cancelScheduledEmail(self, scheduledEmailId: str):
        scheduled = self.scheduled.get(str(scheduledEmailId))
        if scheduled is None:
            return None
        scheduled.state = "CANCELLED"
        self._persist(scheduled)
        return scheduled.asDict()

    def listScheduledEmails(self):
        return [item.asDict() for item in sorted(self.scheduled.values(), key=lambda item: item.sendAt)]

    def processDueEmails(self, now: str | None = None):
        now = now or self._now()
        sent = []
        for scheduled in list(self.scheduled.values()):
            if scheduled.state != "PENDING":
                continue
            if scheduled.sendAt and scheduled.sendAt > now:
                continue
            try:
                sentPayload = self.sendManager.sendEmail(accountId=scheduled.draft.accountId, draftId=scheduled.draft.draftId, metadata=scheduled.metadata)
                scheduled.state = "SENT"
                self._persist(scheduled)
                sent.append(sentPayload)
                self._emit("email.sent", sentPayload)
            except Exception as error:
                scheduled.state = "FAILED"
                scheduled.metadata = {**dict(scheduled.metadata or {}), "error": str(error)}
                self._persist(scheduled)
                self._emit("email.failed", {"scheduledEmailId": scheduled.scheduledEmailId, "error": str(error)})
        return sent

    def snapshot(self):
        return {"available": True, "scheduledCount": len(self.scheduled)}

    def _resolveDraft(self, accountId: str, draftId: str, fields: dict[str, Any]):
        if self.sendManager is not None and draftId:
            existing = self.sendManager.draftManager.getDraft(draftId) if self.sendManager.draftManager is not None else None
            if existing is not None:
                return existing
        return EmailDraft.fromDict(
            {
                "draftId": draftId,
                "accountId": accountId,
                "to": list(fields.get("to") or []),
                "cc": list(fields.get("cc") or []),
                "bcc": list(fields.get("bcc") or []),
                "subject": str(fields.get("subject") or ""),
                "body": str(fields.get("body") or ""),
                "attachments": [dict(item) for item in (fields.get("attachments") or [])],
                "metadata": dict(fields.get("metadata") or {}),
            }
        )

    def _createScheduleItem(self, scheduled: ScheduledEmail):
        scheduleModule = getattr(self.context, "personalSchedule", None)
        if scheduleModule is None or not hasattr(scheduleModule, "createScheduleItem"):
            return None
        try:
            title = "Draft"
            if scheduled.draft.subject:
                title = scheduled.draft.subject
            elif scheduled.draft.to:
                title = scheduled.draft.to[0]
            return scheduleModule.createScheduleItem(
                title=f"Send email: {title}",
                description=scheduled.draft.body,
                type="REMINDER",
                dueTime=scheduled.sendAt,
                priority="NORMAL",
                metadata={"emailScheduledEmailId": scheduled.scheduledEmailId, **dict(scheduled.metadata or {})},
            )
        except Exception:
            return None

    def _scheduleItemIdFor(self, draft: EmailDraft, sendAt: str):
        return f"email-{draft.accountId}-{draft.draftId}-{sendAt}"

    def _persist(self, scheduled: ScheduledEmail):
        if self.store is not None:
            self.store.upsertScheduledEmail(scheduled.asDict())

    def _loadPersisted(self):
        if self.store is None:
            return
        for row in self.store.listScheduledEmails():
            scheduled = ScheduledEmail.fromDict(row)
            if scheduled.scheduledEmailId:
                self.scheduled[scheduled.scheduledEmailId] = scheduled

    def _emit(self, name: str, payload: dict[str, Any]):
        eventBus = getattr(self.context, "eventManager", None)
        if eventBus is None:
            return None
        try:
            return eventBus.emit(name, payload or {})
        except Exception:
            return None

    @staticmethod
    def _newId(prefix: str):
        from uuid import uuid4

        return f"{prefix}-{uuid4().hex[:12]}"

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()
