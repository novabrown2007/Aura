"""Abstract email provider implementation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from modules.email.models import EmailAccount, EmailConnectionState, EmailDraft, EmailLabel, EmailMessage, EmailProviderType


class EmailProvider:
    """Deterministic base provider for Aura email accounts."""

    providerType = EmailProviderType.UNKNOWN

    def __init__(self, context=None):
        self.context = context
        logger = getattr(context, "logger", None)
        self.logger = logger.getChild(f"Email.Provider.{self.providerType}") if logger else None
        self.available = True
        self.accounts: dict[str, EmailAccount] = {}
        self.inboxes: dict[str, list[EmailMessage]] = {}
        self.sent: dict[str, list[EmailMessage]] = {}
        self.drafts: dict[str, dict[str, EmailDraft]] = {}
        self.labels: dict[str, list[EmailLabel]] = {}

    def initialize(self, context=None):
        if context is not None:
            self.context = context
        return self

    def isAvailable(self):
        return bool(self.available)

    def connectAccount(self, account):
        account = EmailAccount.fromDict(account.asDict() if hasattr(account, "asDict") else dict(account or {}))
        account.providerType = EmailProviderType.normalize(account.providerType or self.providerType)
        account.connectionState = EmailConnectionState.CONNECTED
        account.lastSyncTime = self._now()
        self.accounts[account.accountId] = account
        self.inboxes.setdefault(account.accountId, self._seedInbox(account))
        self.sent.setdefault(account.accountId, [])
        self.drafts.setdefault(account.accountId, {})
        self.labels.setdefault(account.accountId, self._seedLabels())
        return account

    def listInbox(self, accountId: str, limit: int = 25):
        messages = list(self.inboxes.get(str(accountId), []))
        messages.sort(key=lambda item: item.receivedAt, reverse=True)
        return [message.asDict() for message in messages[: max(0, int(limit or 25))]]

    def readEmail(self, accountId: str, messageId: str):
        message = self._findMessage(accountId, messageId)
        if message is None:
            return None
        message.isUnread = False
        return message.asDict()

    def searchEmails(self, accountId: str, query: str):
        query = str(query or "").strip().lower()
        results = []
        for message in self.inboxes.get(str(accountId), []):
            if self._matches(message, query):
                results.append(message.asDict())
        return results

    def createDraft(self, accountId: str, draft):
        draft = EmailDraft.fromDict(draft.asDict() if hasattr(draft, "asDict") else dict(draft or {}))
        draft.accountId = str(accountId)
        draft.draftId = draft.draftId or self._newId("draft")
        draft.createdAt = draft.createdAt or self._now()
        draft.updatedAt = self._now()
        self.drafts.setdefault(str(accountId), {})[draft.draftId] = draft
        return draft

    def sendEmail(self, accountId: str, draftOrMessage):
        if isinstance(draftOrMessage, EmailDraft):
            draft = draftOrMessage
        else:
            draft = EmailDraft.fromDict(draftOrMessage)
        accountId = str(accountId or draft.accountId or "")
        if not accountId:
            raise ValueError("Email account is required.")
        sent = EmailMessage(
            messageId=self._newId("sent"),
            accountId=accountId,
            threadId=draft.metadata.get("threadId", ""),
            sender=self.accounts.get(accountId, EmailAccount(accountId=accountId)).emailAddress,
            recipients=list(draft.to or []),
            cc=list(draft.cc or []),
            bcc=list(draft.bcc or []),
            subject=str(draft.subject or ""),
            snippet=self._snippet(draft.body),
            body=str(draft.body or ""),
            receivedAt=self._now(),
            sentAt=self._now(),
            isUnread=False,
            isImportant=False,
            labels=[],
            tags=list((draft.metadata or {}).get("tags") or []),
            attachments=[dict(item) for item in draft.attachments or []],
            metadata={"provider": self.providerType, **dict(draft.metadata or {})},
        )
        self.sent.setdefault(accountId, []).append(sent)
        self._deleteDraft(accountId, draft.draftId)
        return sent.asDict()

    def applyLabel(self, accountId: str, messageId: str, label: str):
        message = self._findMessage(accountId, messageId)
        if message is None:
            return None
        if label not in message.labels:
            message.labels.append(label)
        return message.asDict()

    def listLabels(self, accountId: str):
        return [label.asDict() for label in self.labels.get(str(accountId), [])]

    def removeLabel(self, accountId: str, messageId: str, label: str):
        message = self._findMessage(accountId, messageId)
        if message is None:
            return None
        message.labels = [item for item in message.labels if item != label]
        return message.asDict()

    def deleteEmail(self, accountId: str, messageId: str):
        inbox = self.inboxes.get(str(accountId), [])
        for index, message in enumerate(list(inbox)):
            if message.messageId == str(messageId):
                inbox.pop(index)
                return message.asDict()
        return None

    def archiveEmail(self, accountId: str, messageId: str):
        message = self._findMessage(accountId, messageId)
        if message is None:
            return None
        if "Archive" not in message.labels:
            message.labels.append("Archive")
        return message.asDict()

    def listDrafts(self, accountId: str):
        return [draft.asDict() for draft in self.drafts.get(str(accountId), {}).values()]

    def shutdown(self):
        return None

    def snapshot(self):
        return {
            "providerType": self.providerType,
            "available": self.available,
            "accounts": [account.asDict() for account in self.accounts.values()],
            "inboxCounts": {accountId: len(messages) for accountId, messages in self.inboxes.items()},
            "draftCounts": {accountId: len(items) for accountId, items in self.drafts.items()},
            "labelCounts": {accountId: len(items) for accountId, items in self.labels.items()},
        }

    def _findMessage(self, accountId: str, messageId: str):
        for message in self.inboxes.get(str(accountId), []):
            if message.messageId == str(messageId):
                return message
        return None

    def _deleteDraft(self, accountId: str, draftId: str):
        self.drafts.get(str(accountId), {}).pop(str(draftId), None)

    def _seedInbox(self, account: EmailAccount):
        now = datetime.now(timezone.utc)
        base = [
            EmailMessage(
                messageId=self._newId("msg"),
                accountId=account.accountId,
                threadId=self._newId("thread"),
                sender="support@example.com",
                recipients=[account.emailAddress],
                subject=f"Welcome to {self.providerType.title()} Mail",
                snippet="Your inbox is ready.",
                body="Your inbox is ready.",
                receivedAt=(now - timedelta(minutes=2)).isoformat(),
                isUnread=True,
                isImportant=False,
                labels=["Inbox"],
                tags=["welcome"],
                attachments=[],
                metadata={"provider": self.providerType},
            ),
            EmailMessage(
                messageId=self._newId("msg"),
                accountId=account.accountId,
                threadId=self._newId("thread"),
                sender="news@example.com",
                recipients=[account.emailAddress],
                subject="Weekly newsletter",
                snippet="A short update from your subscriptions.",
                body="A short update from your subscriptions.",
                receivedAt=(now - timedelta(minutes=1)).isoformat(),
                isUnread=True,
                isImportant=False,
                labels=["Inbox"],
                tags=["newsletter"],
                attachments=[],
                metadata={"provider": self.providerType},
            ),
        ]
        return base

    def _seedLabels(self):
        return [
            EmailLabel(labelId="inbox", name="Inbox", system=True),
            EmailLabel(labelId="archive", name="Archive", system=True),
            EmailLabel(labelId="important", name="Important", system=True),
        ]

    def _matches(self, message: EmailMessage, query: str):
        if not query:
            return True
        haystack = " ".join(
            [
                message.sender,
                message.subject,
                message.snippet,
                message.body,
                " ".join(message.recipients or []),
                " ".join(message.labels or []),
                " ".join(message.tags or []),
            ]
        ).lower()
        return query in haystack

    @staticmethod
    def _snippet(text: str) -> str:
        return str(text or "")[:140]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _newId(prefix: str) -> str:
        from uuid import uuid4

        return f"{prefix}-{uuid4().hex[:12]}"
